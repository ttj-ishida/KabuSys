# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従って管理しています。  

注意: バージョン番号はパッケージメタデータ (src/kabusys/__init__.py の __version__) と整合しています。

## [Unreleased]

- (なし)

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能とモジュールを実装しています。

### 追加 (Added)

- パッケージ基盤
  - パッケージエントリポイントとバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを追加。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装：コメント、export 形式、クォート文字列、エスケープ処理、インラインコメントの取り扱いに対応。
  - OS 環境変数を保護する機能（protected set）や override フラグをサポート。
  - Settings クラスを導入し、アプリ固有設定をプロパティ経由で提供：
    - J-Quants / kabuステーション / Slack / DB パス等の設定（必須値は _require により検証）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値の定義）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（OpenAI）統合 (kabusys.ai)
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols を銘柄ごとに集約し、gpt-4o-mini（JSON mode）へバッチ送信してスコアリング。
    - スコアリングは銘柄ごとに最大記事数／文字数でトリム（トークン肥大対策）。
    - レスポンス検証機能（JSON の抽出、構造チェック、スコア型検証、既知コード照合、スコア ±1.0 クリップ）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx を対象）と指数バックオフ実装。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock で patch）。
    - ニュース収集ウィンドウ計算（JST 基準）を実装（calc_news_window）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - raw_news からマクロキーワードで記事抽出、LLM で macro_sentiment を取得（gpt-4o-mini、JSON mode）。
    - API エラー時は macro_sentiment = 0.0 のフェイルセーフ。
    - リトライ/バックオフ、JSON パース耐性、スコアクリップ等を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時の ROLLBACK とログ）。

- データ処理 / ETL (kabusys.data)
  - ETL 結果表現（ETLResult）と pipeline モジュールの公開（kabusys.data.etl / pipeline）。
    - ETLResult はデータクラス化され、品質チェック結果やエラー情報を含む。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの存在確認、カレンダー取得／差分保存（J-Quants での差分取得を想定）。
    - 営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB にデータがない場合は曜日フォールバック（土日を非営業日扱い）。
    - 夜間バッチ更新ジョブ（calendar_update_job）: lookahead/backfill/健全性チェックを導入。
    - 最大探索日数制限や NULL 値取り扱いに関する安全策を実装。
  - ETL パイプライン骨組み（kabusys.data.pipeline）
    - 差分取得、backfill、品質チェックのフレームワークを実装。
    - DuckDB を前提とした最大日付取得ユーティリティ、テーブル存在チェック等。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算群（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金/volume_ratio）を計算する関数を実装（calc_momentum / calc_value / calc_volatility）。
    - DuckDB SQL を活用したウィンドウ関数ベースの実装。データ不足時は None を返す設計。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンに対する将来リターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランクで処理）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリのみで算出。
    - ランク関数（rank）と小規模ユーティリティを提供。
  - データ統合
    - zscore_normalize を kabusys.data.stats から再エクスポート。

### 変更 (Changed)

- 設計方針（全体）
  - ルックアヘッドバイアス回避: datetime.today() / date.today() を直接参照しない設計を徹底（関数引数で基準日を受け取り deterministics に処理）。
  - DuckDB を主要なローカル分析ストアとして採用し、SQL ウィンドウ関数を多用して高効率に集計を行う方針を採用。
  - 外部 API 呼び出しはフェイルセーフ（例外を全体の停止にしない）で設計し、部分失敗を許容することで堅牢性を高める。

### 修正 (Fixed)

- 初回リリースのための基盤的なエラー対策とログ出力を多数導入（API 呼び出し失敗時の警告/リトライ、DB 書込時の ROLLBACK ハンドリングなど）。

### テスト支援 / 拡張性

- OpenAI 呼び出しの内部ラッパー関数（_call_openai_api）が各モジュールで定義されており、ユニットテスト時に patch してモック化できるように設計。
- 設定の自動読み込みを無効にするフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）によりテスト実行環境を制御可能。

### 既知の制約 / 注意点

- 現バージョンでは gpt-4o-mini を前提とした JSON mode を利用する実装になっており、OpenAI SDK の将来的な変更に影響を受ける可能性があります。API エラー時はフォールバック動作（スコア 0.0 や処理スキップ）を行うため、結果の欠損に留意してください。
- DuckDB の executemany に関する互換性（空リストを渡せない等）を考慮した実装上の注意（空パラメータ時の分岐）があります。
- raw_financials に基づく PBR/配当利回りは現時点で未実装。

---

このリリースは、KabuSys の自動売買・データプラットフォームのコア基盤（データ取得・カレンダ管理・ファクター計算・AI によるニュース評価・レジーム判定）を一通り備えた初期公開版です。今後はモジュールの追加、既存ロジックのチューニング、テストカバレッジ拡充やドキュメント整備を行っていく予定です。