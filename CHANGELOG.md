# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。  
初回リリースとして v0.1.0 を作成しました（リリース日: 2026-04-03）。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を実装しています。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。
  - パッケージ主要モジュール群を公開: data, strategy, execution, monitoring。

- 環境設定/ユーティリティ (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動的に読み込む自動ロード実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索し、パッケージ配布後も CWD に依存しない動作を実現。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートやバックスラッシュエスケープ処理、コメント処理）。
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスでアプリケーション設定を統一管理（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定 / ログレベル検証 等）。
  - 必須環境変数未設定時は明示的に ValueError を発生させる _require() を採用。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を使用して銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC へ変換）を calc_news_window として提供。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりのトークン肥大化対策（最大記事数・最大文字数トリム）。
    - レスポンスの堅牢な検証（JSON 抽出、results 構造検証、コード正規化、数値チェック）とスコアのクリップ。
    - リトライとエラーハンドリング（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに冪等書き込み。
    - マクロニュースはマクロワードでフィルタして gpt-4o-mini に投げる。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - OpenAI 呼び出しは内部実装（news_nlp とは別でモジュール結合を避ける）。
    - API キーは引数で注入可能（テスト性向上）。

- 研究・ファクター分析 (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高指標）、Value（PER、ROE）などの定量ファクターを実装。
    - DuckDB 上の SQL とウィンドウ関数を活用し、(date, code) 単位の結果リストを返す設計。
    - データ不足時の None 扱い等、堅牢な欠損処理。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns)：複数ホライズンに対応、入力検証あり。
    - IC（Information Coefficient）計算 (calc_ic)：スピアマンのランク相関を実装（最小有効レコード 3）。
    - ランク変換 (rank) とファクター統計サマリー (factor_summary) を実装。
  - 研究ユーティリティの再エクスポート（zscore_normalize など）。

- データプラットフォーム (src/kabusys/data/)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダーを保持する market_calendar テーブルを用いた営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先、未登録日は曜日ベースでフォールバック。探索上限（日数）を設定して無限ループ防止。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得・バックフィル・保存を行う。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETL 結果を表す ETLResult dataclass を公開（取得件数、保存件数、品質問題、エラー一覧など）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）やエラーハンドリング設計。
    - jquants_client との疎結合化を図り、idempotent な保存（ON CONFLICT）を想定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 設計上の注意点 / 制約 (Notes)
- DuckDB を主要ストレージとして利用（SQL は DuckDB を前提）。DuckDB のバージョン差異（例: executemany に空リストを渡せない等）を意識した実装上の配慮あり。
- 外部依存:
  - OpenAI API（gpt-4o-mini）に依存する処理が複数存在。API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定する必要あり。
  - J-Quants クライアント経由でのデータ取得を前提（JQUANTS_REFRESH_TOKEN 等の環境変数が必要）。
- ルックアヘッドバイアスへの対策:
  - 各種処理で datetime.today()/date.today() を直接参照しない（target_date を明示的に渡す設計）。
  - DB クエリは常に target_date 未満 / 以前の条件を守るよう実装。
- フェイルセーフ:
  - LLM 呼び出しの失敗時は例外を投げずに 0.0 や空スコアでフォールバックし、処理を継続する設計（運用上の安定性重視）。
- トランザクション:
  - DB 書き込みは明示的な BEGIN / DELETE / INSERT / COMMIT を使用し、例外時は ROLLBACK を試行。ROLLBACK 失敗時は警告ログを出力して上位へ例外を伝播。
- テスト性:
  - OpenAI 呼び出し部分は内部関数を patch で差し替え可能にしてユニットテストを容易にしている。
  - 環境変数自動読み込みをテスト中に無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

### マイグレーション / 初期設定 (Upgrade / Setup)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（AI スコアリングを使う場合）
- 推奨設定:
  - .env/.env.local に設定を記載し、プロジェクトルート（.git または pyproject.toml があるディレクトリ）に配置すると自動ロードされる。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DB:
  - デフォルトでは DuckDB のパスは data/kabusys.duckdb、監視用 SQLite は data/monitoring.db。必要に応じて DUCKDB_PATH / SQLITE_PATH を設定。

---

今後のリリースでは、strategy / execution / monitoring の具体的な注文実行ロジックや運用監視機能の追加、テストカバレッジ・ドキュメントの拡充、及び外部 API のエラーハンドリング改善を予定しています。問題報告・機能提案は Issue を作成してください。