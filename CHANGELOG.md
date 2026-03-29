# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリースノートは安定した API と主要な実装方針（ルックアヘッドバイアス回避、冪等性、フェイルセーフ等）を中心に記載しています。
- 主要な公開 API / エントリポイントは README / ドキュメント参照を推奨しますが、下記に実装済みの機能を要約しています。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ で公開モジュール: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env の行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - .env 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定のみ）。
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants, kabu API, Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、環境種別（development/paper_trading/live）、ログレベルなど。
  - 設定バリデーションを実装（KABUSYS_ENV と LOG_LEVEL の許容値チェック、必須環境変数未設定時に ValueError）。

- ニュース NLP（OpenAI 統合） (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols に基づき、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へ投げ、センチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window 関数として提供。
  - 1チャンク最大 20 銘柄のバッチ処理、1銘柄あたりの記事数と文字数制限、チャンクごとのリトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
  - レスポンス検証ロジック（JSON 抽出・"results" キー・コード整合性・数値チェック）を実装。無効レスポンスはスキップして処理継続（フェイルセーフ）。
  - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを誤って削除しないよう、DELETE→INSERT の手法で置換を実行（影響範囲をコードで限定）。
  - テスト容易性のため、内部の OpenAI 呼び出し関数をパッチ差し替え可能に設計。

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - prices_daily と raw_news を参照して ma200_ratio を計算、ニュースはマクロキーワードでフィルタして LLM（gpt-4o-mini）でセンチメントを算出。
  - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装し、リトライ（指数バックオフ）を行う。
  - 出力は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
  - ルックアヘッドバイアス対策を仕様に明記（target_date 未満のデータのみ使用、datetime.today() を直接参照しない）。

- Research / ファクター計算 (src/kabusys/research)
  - factor_research.py: モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）などのファクター計算関数を実装（DuckDB SQL を活用）。
  - feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）、ランク関数、およびファクター統計サマリーを実装。外部依存（pandas 等）を用いず標準ライブラリで実装。
  - research パッケージで主要関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- Data プラットフォーム機能 (src/kabusys/data)
  - calendar_management.py:
    - JPX カレンダー（market_calendar）関連ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録がない日については曜日ベースのフォールバック（平日を営業日）を行う方針を採用。DB が部分的にしかない場合でも一貫した判定となる実装。
    - calendar_update_job を実装（J-Quants から差分取得し保存。バックフィル、健全性チェックあり）。
  - pipeline.py / etl.py:
    - ETLResult データクラスを公開（ETL の実行結果・品質問題・エラーの集約）。
    - ETL パイプラインの設計方針とユーティリティ関数を実装（差分取得、バックフィル、品質チェックの扱いなど）。
    - DuckDB に依存するヘルパー（テーブル存在チェック、最大日付取得）を実装。

- DuckDB を主要なローカルデータストアとして利用
  - 多くの処理で DuckDB 接続を引数に取り、SQL と組み合わせた処理を実装（prices_daily, raw_news, ai_scores, raw_financials, market_calendar などを参照）。

### 変更 (Changed)
- 初回リリースのため、API/仕様の初期設計を確定。
- 設計方針として共通して下記を採用:
  - ルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照しない）。
  - 外部注文 API 等にアクセスしない（research などの分析用モジュールは読み取り専用）。
  - 冪等性を重視した DB 書き込み（DELETE→INSERT、ON CONFLICT 想定）。
  - フェイルセーフ（外部 API 失敗時はスキップ／デフォルト値を使い処理継続）。

### 修正 (Fixed)
- （初版公開のため特記すべきバグフィックス履歴はなし）

### 破壊的変更 (Breaking Changes)
- 0.1.0 は初リリースのため破壊的変更はありません。ただし、以下を利用前に必ず確認してください:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）未設定時は Settings のプロパティ参照で ValueError が発生します。
  - OpenAI を利用する score_news / score_regime は OPENAI_API_KEY（もしくは api_key 引数）必須。
  - DuckDB スキーマ（テーブル名・カラム）に依存するため、期待するテーブル構造がない場合は例外が発生する可能性があります。

### 開発者向けメモ
- テスト容易性のため、各モジュール内の OpenAI 呼び出し関数（_call_openai_api）は unittest.mock.patch で置き換え可能な形で実装されています。
- .env パーサは POSIX の多くのケース（export プレフィックス、引用符、エスケープ、インラインコメントなど）に対応していますが、極端に特殊なケースは未カバーの可能性があります。
- DuckDB に対する executemany の互換性問題（空リストバインド不可）を回避するため、空チェックを行っています。

---

（今後のリリースでは機能追加、性能改善、既知の問題修正等をカテゴリ別に追記します。）