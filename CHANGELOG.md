# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-01

初回リリース。本バージョンでは、日本株自動売買システムの基盤となる以下の主要コンポーネントを実装しています。

### 追加 (Added)
- パッケージのエントリポイント
  - kabusys パッケージを公開（version = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に宣言）。

- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env/.env.local ファイルおよび OS 環境変数から設定値を読み込み。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 依存を排除）。
  - .env パーサ実装:
    - export KEY=VAL 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - コメント（#）の扱いを文脈依存で正しく解析。
  - 自動ロードの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）等のプロパティ。
    - 必須値未設定時は ValueError を送出。
    - env / log_level のバリデーションを実装。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI 関連: ニューススコアリングと市場レジーム判定
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - チャンク単位（デフォルト 20 銘柄）で処理。1 銘柄あたり最大記事数と文字数でトリム。
    - JSON Mode での応答検証・パースロジック実装（前後の余計なテキストを取り除く復元ロジック含む）。
    - リトライ/指数バックオフ（429/ネットワーク/タイムアウト/5xx 対応）。致命的でない場合はスキップし継続（フェイルセーフ）。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - calc_news_window: タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換して扱う）。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供（戻り値: 書き込んだ銘柄数）。
    - OpenAI API キー注入対応（引数または環境変数 OPENAI_API_KEY）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み 70% / 30% で合成して日次レジーム ('bull'/'neutral'/'bear') を判定。
    - マクロキーワードで raw_news をフィルタし、最大記事数を LLM に渡す。
    - LLM 呼び出しは独立実装（モジュール間結合低減）。
    - API エラー時は macro_sentiment=0.0 にフォールバック（継続処理）。
    - 判定値を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) を提供（戻り値: 1=成功）。

- リサーチ／ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20 日）、平均売買代金、出来高比率、PER/ROE（raw_financials ベース）を計算する関数を実装。
    - DuckDB 上で SQL ウィンドウ関数を用い高効率に実装。データ不足時は None を返す扱い。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic: Spearman の ρ をランクで計算）。
    - ランク変換ユーティリティ (rank) とファクター統計サマリ (factor_summary) を実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装。
  - research パッケージ __init__ で主要関数を再エクスポート。

- データ基盤 (src/kabusys/data/)
  - calendar_management.py
    - market_calendar テーブルに基づく営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB がまばらな場合でも一貫した振る舞いを保つため、DB 登録値優先かつ未登録日は曜日ベースでフォールバック。
    - 夜間バッチ job (calendar_update_job) を実装。J-Quants API からの差分取得と保存（バックフィルと健全性チェックあり）。
  - ETL パイプラインの基礎 (src/kabusys/data/pipeline.py, etl.py)
    - ETLResult データクラスを実装（取得数／保存数／品質問題／エラーの集約）。
    - pipeline の基本方針（差分更新・バックフィル・品質チェックの扱い）を実装方針として定義。
    - data.etl から ETLResult を再エクスポート。

- 依存／実行上の注意
  - DuckDB ベースのデータ操作を前提（DuckDB 接続オブジェクトを引数として受け取る API を多数提供）。
  - OpenAI SDK（OpenAI クライアント）経由で gpt-4o-mini を利用する設計（JSON Mode を期待）。
  - ロギングを各モジュールに追加し、処理状況や失敗時に情報を出力。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制約・注意事項 (Known issues / Notes)
- OpenAI API のレスポンスが期待通りの JSON 形式でない場合、復元ロジックで対応するが完全保証はない（不正応答はそのチャンクをスキップして継続する設計）。
- DuckDB の executemany に関する互換性対応を行っている（空リストバインドを避ける等）。
- 一部の公開サブパッケージ（strategy, execution, monitoring）の詳細実装は本稿に含まれていないか、別ファイルに実装される想定。
- 設定値や API キーは適切に環境変数または .env に設定する必要がある（未設定時は ValueError を送出する箇所あり）。

### マイグレーション / 導入手順 (Migration / Upgrade notes)
- 必要な環境変数:
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（データ取得等で必須）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知機能利用時）
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB/SQLite のデータベースパスは Settings クラスのプロパティ（DUCKDB_PATH/SQLITE_PATH）で上書き可能。

---

将来のリリースでは、strategy/execution/monitoring の具体的実装、追加の品質チェックルール、テスト・CI の拡充、運用向けの監視・アラート機能の拡張を予定しています。