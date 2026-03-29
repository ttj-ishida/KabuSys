# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルは、ソースコードの内容から推測して作成した初期の変更履歴です。

## [Unreleased]
- 今後の改善予定（例）:
  - ai モジュールのテストカバレッジ拡張（外部 API モックの整備）
  - ETL の並列処理や部分再実行の仕組み追加
  - docs / リファレンスの整備（API 使用例・データスキーマ）

---

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システムのコア機能を実装した最初のバージョン。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, ...）を公開。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック(_find_project_root)を実装し、配布後も CWD に依存しない環境変数読み込みを実現。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理等）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベルなどのプロパティ、入力バリデーションを含む）。
  - 環境値の必須チェックで未設定時に ValueError を送出するヘルパーを提供。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄毎のセンチメントを LLM（gpt-4o-mini）で評価し、ai_scores テーブルへ書き込む。
    - チャンク処理（最大20銘柄/コール）、トリミング（記事数・文字数制限）、JSON Mode レスポンスパース、厳密なレスポンス検証ロジックを実装。
    - API エラー（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップする設計。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。
    - ニュース時間ウィンドウ計算（JST基準）を提供（calc_news_window）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ書き込み。
    - マクロニュース抽出、OpenAI 呼び出し、スコア合成、閾値判定（bull/neutral/bear）を実装。
    - API エラー時に macro_sentiment=0.0 へフォールバックするフェイルセーフ動作。
    - OpenAI クライアントは明示的な API キー解決（引数優先→環境変数）を行う。
- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - JPX カレンダーを扱うための market_calendar テーブル操作、営業日判定 (is_trading_day)、次/前営業日検索 (next_trading_day / prev_trading_day)、期間内営業日取得 (get_trading_days)、SQ日判定 (is_sq_day) を実装。
    - DB 値優先、未登録日は曜日ベースのフォールバック、最大探索幅制限、安全性チェック（将来日付の異常検出）などを備える。
    - 夜間バッチ更新ジョブ calendar_update_job により J-Quants クライアントを用いた差分取得と保存を実装（バックフィルと健全性チェックあり）。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを実装し、ETL 実行結果の集約・シリアライズを提供。
    - 差分更新ロジック、最終取得日の算出、データ取得→保存→品質チェックの流れを想定したユーティリティ実装。
    - jquants_client と quality モジュールを統合するためのインターフェースを準備。
- Research モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、ma200乖離）、Volatility（20日 ATR、相対 ATR、出来高関連）、Value（PER、ROE）等を DuckDB SQL とウィンドウ関数で実装。
    - データ不足時の None ハンドリングを含む。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（forward returns）、IC（Spearman rank / ランク相関）計算、ランク変換ユーティリティ、カラム統計サマリーを実装。
    - 標準ライブラリのみで実装し外部依存を排除。
  - data.stats からの zscore_normalize の再エクスポートを提供（research.__init__）。
- インフラ / 設計上の配慮
  - DuckDB をコアのデータストアとして利用（DuckDBPyConnection を想定）。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の利用）。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照しない設計（target_date を明示的に渡す）。
  - OpenAI 呼び出し・レスポンス処理は堅牢なバリデーションとクリッピング（スコア範囲制限）を実装。
  - ログ出力を各モジュールで活用（logger の利用、警告/情報/デバッグログによる観察性確保）。
  - 環境変数で Slack トークン / チャンネル、kabu API パスワード、J-Quants トークン、DB パス等を設定可能。

### 変更 (Changed)
- 初版のため過去バージョンからの変更は無し。

### 修正 (Fixed)
- 初版のため修正項目は無し。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- 初版のため既知の重大なセキュリティ修正は無し。  
  注意点:
  - OpenAI API キーや Slack トークン等の機密情報は環境変数で管理する設計。ローカル .env ファイルの取り扱いに注意してください。
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

備考:
- 実装はテストフレンドリーになるように設計されています（OpenAI 呼び出しの差し替え、明示的な target_date 指定など）。  
- 実運用時は環境変数の設定（.env/.env.local の作成）と DuckDB スキーマ（prices_daily, raw_news, market_calendar, ai_scores, raw_financials 等）の準備が必要です。