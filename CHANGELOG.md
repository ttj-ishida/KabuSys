# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
なお本CHANGELOGはリポジトリ内のソースコードを基に推測して作成した初期リリース向けの記録です。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-27
初期リリース

### 追加 (Added)
- パッケージの公開
  - kabusys パッケージを追加。トップレベルで data, strategy, execution, monitoring などを公開（__all__ によるエクスポート）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み機能を実装。優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用）。
  - .env 行パーサ実装（export プレフィックス対応、クォート処理、インラインコメント処理）。  
  - 読み込み時に既存の OS 環境変数を保護する protected 機構を採用。
  - 設定アクセス用 Settings クラスを追加。必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）とデフォルト値（KABU_API_BASE_URL、DB パス等）、KABUSYS_ENV / LOG_LEVEL の検証ロジック、利便性プロパティ（is_live / is_paper / is_dev）を提供。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール（score_news）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini／JSON Mode）へバッチ送信して銘柄別センチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）機能を実装（calc_news_window）。
    - バッチサイズ、記事数上限、文字数トリム、リトライ（429・ネットワーク・タイムアウト・5xx）・指数バックオフ実装。
    - レスポンスの厳格なバリデーションと数値クリッピング（±1.0）。部分失敗時の DB 保護（対象コードのみ DELETE→INSERT）や DuckDB executemany の空配列制約への対応を実装。
    - API 呼び出し部はテスト差し替え可能（_call_openai_api の patch を想定）。
  - regime_detector モジュール（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースに対する LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次判定を書き込む機能を実装。
    - マクロ記事抽出は news_nlp 側の窓計算を利用、OpenAI 呼び出し独立実装、API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の安全処理を実装。
    - リトライ・バックオフ、JSON パースの堅牢化（パース失敗時のログとフォールバック）を実装。

- リサーチ／ファクター計算 (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）等の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を用いた計算、データ不足時の None 処理、結果は (date, code) キーの辞書リストとして返却。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）へのリターンを計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装、最小有効レコード数チェック。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
  - kabusys.research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

- データプラットフォーム (kabusys.data)
  - calendar_management モジュール
    - market_calendar テーブルを前提に営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 日判定（is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（平日）でフォールバックする設計。
    - 夜間バッチ更新 job（calendar_update_job）を追加：J-Quants API から差分取得、バックフィル、健全性チェック（将来日が異常に遠い場合はスキップ）、保存は jquants_client 経由で冪等に行う。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を行うパイプライン設計（jquants_client を用いた保存、エラーは収集して上位で判断する方針）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 共通設計上の注意点（ドキュメント的追加）
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を不用意に参照しない設計（多くの関数は target_date 引数を受ける）。
  - DuckDB を用いた SQL 処理が中心。DB 書き込みは可能な限り冪等に設計（DELETE→INSERT や ON CONFLICT を前提）。
  - OpenAI API 呼び出しに対してはリトライ、バックオフ、エラー時のフォールバック（スコア 0.0）でフェイルセーフを確保。
  - テスト容易性を考慮し、API 呼び出し関数をパッチ可能に分離。

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- なし（初期リリース）

### 削除 (Removed)
- なし（初期リリース）

### 廃止 (Deprecated)
- なし（初期リリース）

### セキュリティ (Security)
- OpenAI API キー（OPENAI_API_KEY）は明示的に与える必要がある（api_key 引数または環境変数）。キーが未設定の場合は ValueError を送出して処理を中止。
- 環境ファイル読み込み時に既存 OS 環境変数を上書きしないデフォルト動作、及び保護セット(protected)を用いることで OS 側の機密設定を保護。

---

補足:
- 本 CHANGELOG はコードベースの実装仕様・設計コメントを基に作成しており、実際のリリースノートやドキュメントは別途ビルド・テストの結果や外部連携（J-Quants, OpenAI, Slack 等）実装状況に応じて更新してください。