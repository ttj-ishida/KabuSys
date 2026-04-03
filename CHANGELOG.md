# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルには、パッケージのリリースごとの主要な追加・変更点・修正点を記載します。

## [Unreleased]
- 次回リリースに向けた変更点はここに記載します。

## [0.1.0] - 2026-04-03
初回公開リリース。

### 追加
- パッケージ基盤
  - パッケージメタ情報を設定（kabusys.__version__ = "0.1.0"）。公開 API として data/strategy/execution/monitoring を __all__ に公開。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定ロード機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env 自動読み込みを実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env と .env.local の読み込み優先度を明確化（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）。
  - export KEY=val 形式、クォートやエスケープ、インラインコメントの取り扱いなど、.env 行パースロジックを実装。
  - 必須環境変数取得用の _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等のアクセサ）。
  - 環境変数の検証（KABUSYS_ENV の許可値、LOG_LEVEL の許可値）や便利プロパティ（is_live / is_paper / is_dev）を追加。
  - デフォルトパスや監視用フラグ（PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START）・リソース閾値（CPU/MEM/DISK）を設定可能に。

- データ処理・ETL
  - ETL 結果を表す ETLResult データクラスを追加（品質検査結果、取得/保存件数、エラー一覧を含む）。
  - pipeline モジュール（kabusys.data.pipeline）を実装。差分更新、バックフィル、品質チェックとの連携を想定した設計。
  - ETL のためのユーティリティ公開（kabusys.data.etl で ETLResult を再エクスポート）。

- カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar テーブルの管理、JPX カレンダーの差分取得・夜間バッチ更新 calendar_update_job を実装。
  - 営業日判定ユーティリティを提供：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
  - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
  - 最大探索日数制限やバックフィル、健全性チェック（将来日付の異常検知）を実装。

- 研究用解析 (kabusys.research)
  - ファクター計算モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - Volatility: 20日 ATR（atr_20）、ATR の比率（atr_pct）、20日平均売買代金（avg_turnover）、出来高変化率（volume_ratio）。
    - Value: raw_financials から最新財務を取得し PER/ROE を計算（EPS が 0/欠損 の場合は None）。
  - 特徴量探索モジュールを実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - calc_forward_returns: 任意のホライズン（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）の実装（最小有効レコード数チェックあり）。
    - factor_summary: カラム別 count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを返す安定実装。丸め処理で ties の検出漏れを防止。

- AI（LLM）機能 (kabusys.ai)
  - ニュースNLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI の gpt-4o-mini（JSON mode）により銘柄別センチメント（-1.0〜1.0）を取得して ai_scores テーブルへ保存。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1 銘柄あたりの文字数・記事数トリム（_MAX_CHARS_PER_STOCK/_MAX_ARTICLES_PER_STOCK）を実装。
    - 429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフリトライ、その他エラーはスキップして継続するフェイルセーフ設計。
    - レスポンスの厳密なバリデーションとスコアのクリッピング（±1.0）。部分失敗時に既存スコアを保護するため、対象コードのみを DELETE→INSERT で更新。
    - テスト用に _call_openai_api を patch 可能に設計。
    - ニュース収集ウィンドウ計算（calc_news_window）を提供（JST 前日 15:00 ～ 当日 08:30 を UTC に変換して扱う）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込み。
    - マクロキーワードで raw_news をフィルタし、該当記事がある場合にのみ OpenAI でセンチメントを評価。記事がなければ macro_sentiment=0.0。
    - API 失敗時はフェイルセーフで macro_sentiment=0.0、内部的にリトライロジックを実装。
    - OpenAI 呼び出し関数を news_nlp と分離（モジュール結合を防ぐ）。テスト用に差し替え可能。

### 仕様上の注意 / 設計上の判断（重要）
- ルックアヘッドバイアス対策
  - 各種処理（score_news, score_regime, calc_news_window, ファクター/リターン計算など）は内部で datetime.today() / date.today() を参照しない（caller が target_date を明示する）。DB クエリでも target_date 未満/未満等でルックアヘッドを回避する実装。
- データベース操作
  - DuckDB を中心に SQL+Python ハイブリッドで処理を実装。idempotent な保存（DELETE→INSERT / ON CONFLICT を利用）を重視。
  - DuckDB の executemany に空リストを渡せない点に配慮し、空チェックを行ってから executemany を実行。
- フォールバック・堅牢性
  - OpenAI/API 呼び出し失敗時は例外で全体を停止せず、該当箇所をデフォルト値でフォールバック（例: macro_sentiment=0.0、score_news は該当チャンクをスキップ）する設計。
  - .env 読み込みは I/O エラー時に警告を出してスキップ。
- テスト容易性
  - OpenAI 呼び出しのラッパー関数（各モジュール内の _call_openai_api）を用意し、unittest.mock.patch による差し替えを想定した設計。

### 既知の制約 / 今後の対応候補
- OpenAI のモデルと JSON Mode（gpt-4o-mini, response_format）に依存しているため、SDK/API 仕様の変更があれば対応が必要。
- raw_financials からの PBR・配当利回りなどのバリュー指標は未実装（将来的な拡張候補）。
- calendar_update_job の J-Quants クライアント（jquants_client）実装に依存。API 呼び出し失敗時は現在 0 を返す仕様。

---

著者: kabusys 開発チーム  
注: 実装の詳細・理由は各モジュールの docstring に記載しています。必要に応じて README やドキュメントへ追記してください。