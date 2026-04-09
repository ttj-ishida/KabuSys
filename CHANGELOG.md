# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-09

初回リリース。

### 追加
- パッケージのメタ情報
  - kabusys パッケージ初版を提供。パッケージバージョンは __version__ = "0.1.0"。

- 環境設定管理
  - 環境変数および .env ファイルを扱う設定モジュールを追加（kabusys.config）。
  - プロジェクトルートを __file__ を起点に探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - POSIX-ish な .env パース機能を実装（export prefix、シングル/ダブルクォート・エスケープ、行内コメント処理などに対応）。
  - Settings クラスを追加し、J-Quants/OpenAI/kabu/LINE/DB/監視/運用設定をプロパティとして提供。
  - 環境値検証を実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の許容値チェック）。
  - データベースファイルパス（duckdb, sqlite, paper_trading）やプロセス制御ファイル（pid, kill flag）などのデフォルトパスを提供。

- AI（自然言語処理）機能
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントを算出。
    - バッチ処理（1回あたり最大20銘柄）・1銘柄あたりの記事/文字数制限を実装。
    - 再試行・指数バックオフ（429 / ネットワーク断 / タイムアウト / 5xx）を実装。
    - レスポンスの厳密な検証とスコアの ±1.0 クリッピング。
    - DuckDB への冪等的書き込み（該当 code の DELETE → INSERT、executemany の空リスト回避）を実装。
    - API キーは引数で注入可能（テスト容易化）。未設定時は環境変数 OPENAI_API_KEY を参照して ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しに対するリトライ、API エラー時のフォールバック（macro_sentiment=0.0）、およびレスポンス JSON のパース保護を実装。
    - DuckDB の prices_daily / raw_news / market_regime を参照・更新。更新は冪等（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止設計（date 引数ベース、datetime.today() を直接参照しない）。
    - API 呼び出し部分はモジュール内で独立実装（モジュール結合を避ける設計、テスト時に差し替え可能）。

- データプラットフォーム機能（DuckDB ベース）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、J-Quants クライアント経由の保存、品質チェックのフローを想定した ETLResult データクラスを追加。
    - backfill による後出し修正吸収、品質チェック結果の収集（致命的エラーがあっても処理を継続し呼び出し元で判断）設計。
    - ETLResult.to_dict() で品質問題を辞書化して出力可能。

  - ETL 再エクスポート（kabusys.data.etl）
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。

  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアントからの差分取得と保存（ON CONFLICT DO UPDATE）に対応。
    - 営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダー未取得時の曜日ベースフォールバック、DB 登録値優先の一貫した挙動、探索上限（_MAX_SEARCH_DAYS）による安全化を実装。
    - 保存ロジックは健全性チェック（未来日付の異常検出）、バックフィル（日次再フェッチ）を備える。

- リサーチ（因子・特徴量探索）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の prices_daily / raw_financials のみを参照する保守的設計。結果は (date, code) を基本キーにした辞書リストで返す。
    - データ不足時の None 扱い、ウィンドウバッファや安定化のための内部定数を導入。

  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応し一括クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンの ρ をランク化して計算。データ不足時は None を返す。
    - ランク関数（rank）: 同順位は平均ランクを与える実装（丸めによる ties 対応）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。

- パッケージ公開 API
  - 各モジュールで __all__ を適切に設定し、主要関数を再エクスポート（例: kabusys.ai.score_news, kabusys.research の関数群など）。

### 設計上の注意 / 動作上の重要点
- 全体を通して「ルックアヘッドバイアス防止」を重視し、date 引数ベースで処理する設計（datetime.today() を直接参照しない）。
- OpenAI 呼び出しは JSON Mode（厳密な JSON 応答期待）を使用。レスポンスパースに失敗した場合はフェイルセーフ（0.0 やスキップ）で継続する。
- API 再試行（429・ネットワーク断・タイムアウト・5xx）に指数バックオフを適用。上限到達時は該当チャンクをスキップして処理を続行する。
- DuckDB への書き込みは冪等化（DELETE→INSERT 等）を心がけており、executemany に対する空リスト制約を考慮している（DuckDB 0.10 互換性）。
- テストのしやすさを考慮し、OpenAI 呼び出し箇所はモジュール内関数を patch して差し替え可能な構成にしている。

### 既知の制限 / 非対応
- PBR・配当利回りなどの一部バリューファクターは未実装（calc_value では PER・ROE のみ実装）。
- AI スコアやレジーム判定は外部 API（OpenAI）に依存するため、API 利用料・レート制限・キー管理に注意が必要。
- market_calendar の完全な取得には J-Quants クライアント実装が必要（jq.fetch_market_calendar / jq.save_market_calendar を利用）。

### 破壊的変更
- なし（初回リリース）

### セキュリティ
- 現時点で特記すべきセキュリティ脆弱性は報告されていません。環境変数や API キーの管理はユーザー側で適切に行ってください。

---

（今後の変更はこのファイルに逐次追記してください）