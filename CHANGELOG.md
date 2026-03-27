# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ （日本語要約）

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース — コア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。パッケージバージョン __version__ = 0.1.0 を設定。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env / .env.local ファイル及び環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索（cwd に依存しない）。
  - .env パース機能の強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォートあり/なしの差異を考慮）。
    - 読み込み失敗時に警告を出力。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護するための protected キー処理を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用）。
  - Settings クラス提供:
    - J-Quants / kabu-station / Slack / DB パス等のプロパティを定義。
    - 必須変数未設定時は ValueError を送出。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI: ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - score_news(conn, target_date, api_key=None):
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を評価、ai_scores テーブルへ原子性を保って書き込む（DELETE → INSERT の置換方式）。
    - ニュースウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を calc_news_window で提供。
    - バッチ送信（1回で最大 20 銘柄）、1 銘柄あたりの記事数や文字数トリム制御を実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI API 呼び出しは JSON モード利用、429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密バリデーション実装（JSON 抽出・results 配列チェック・code の照合・数値チェック・スコアクリップ）。
    - API 失敗時は該当チャンクをスキップして継続（フェイルセーフ設計）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。

- AI: 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None):
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュース（LLM による macro_sentiment）を合成し日次で市場レジーム（bull / neutral / bear）を判定。
    - 重み付け（MA: 70%、Macro: 30%）・スコア正規化・閾値判定を実装。
    - マクロニュース抽出用キーワードリストを実装（日本・米国・グローバルの代表語）。
    - OpenAI 呼び出しは専用の _call_openai_api を使用し、429/ネットワーク断/タイムアウト/5xx に対するリトライとフェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計（target_date に厳密依存）。

- データ: カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダー操作ユーティリティ:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar テーブルが存在しない場合は曜日ベース（土日除外）でフォールバック。
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した挙動に。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）や健全性チェック（_SANITY_MAX_FUTURE_DAYS）を実装して無限ループや異常値を防止。
  - calendar_update_job(conn, lookahead_days=90):
    - J-Quants クライアント経由で差分取得 → market_calendar に冪等保存。
    - バックフィル（直近 _BACKFILL_DAYS の再取得）と健全性チェックを実装。
    - API エラーや保存失敗時は 0 を返して安全に終了。

- データ: ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を定義して ETL 実行結果を構造化（取得数・保存数・品質問題・エラー等）。
  - ETLResult.to_dict() で品質問題を (check_name, severity, message) に変換して出力可能。
  - パイプライン設計（差分更新・バックフィル・品質チェック・idempotent 保存）を反映するヘルパー関数群を実装（テーブル存在確認・最大日付取得等）。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- リサーチ / 特徴量系 (src/kabusys/research/*)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（prices_daily と結合）。
    - 全関数は DuckDB 上の SQL を主体に実装し、結果を (date, code) をキーとする dict のリストで返す。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）を計算。3 件未満は None を返す。
    - rank: 同順位は平均ランクにするランク関数（丸め処理で ties の誤差を低減）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データアクセス / その他
  - data パッケージ内で jquants_client などの外部クライアント呼び出しを想定したインターフェース設計。

### 変更 (Changed)
- 設計上のポリシーが多数のモジュールに一貫して適用されている点を明確化:
  - ルックアヘッドバイアス防止: date 引数ベースの設計（datetime.today()/date.today() を内部参照しない）。
  - フェイルセーフ設計: 外部 API 失敗時は例外を上位に広げず安全にフォールバック（ただし DB 書き込み等の重要失敗は例外伝播）。
  - DuckDB の互換性考慮（executemany の空リスト制約等）を反映。

### 修正 (Fixed)
- 明示的なバグ修正エントリは初期リリースのため無し。ただし多くの警告・フェイルセーフ・入力バリデーションを追加して実運用時の回復性を向上。

### セキュリティ (Security)
- OpenAI API キーの解決方法を統一（api_key 引数優先、未指定は OPENAI_API_KEY 環境変数を参照）。未設定時は ValueError を送出して誤用を防止。
- 環境変数の自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制約 / 注意点 (Known issues / Notes)
- DuckDB バインドの互換性や executemany の挙動に依存する箇所があり、使用する DuckDB のバージョンによって挙動確認が必要。
- OpenAI 呼び出しは JSON mode を期待するが、稀に余分なテキストが混入するため復元ロジックを入れている。完全な堅牢性のためは運用時にレスポンス確認を推奨。
- 一部のモジュール（例: pipeline の続き）ファイル末尾が存在しない/切れている可能性があり、実装の拡張／統合テストが必要。

---

（注）本 CHANGELOG は与えられたコードベースの内容から実装意図・振る舞いを推測して作成しています。実際のリリースノート作成時はコミットログ・PR 説明・担当者コメント等を参照して差分を確定してください。