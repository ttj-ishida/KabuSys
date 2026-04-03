CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースの内容から推測して作成しています。リリース日や細部は実装に基づく推定です。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開

- 環境設定/管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env のパース機能を細かく実装（export プレフィックス、クォート内のエスケープ、インラインコメント判定などに対応）。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須: 未設定時は ValueError）
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）、監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）
    - リソース閾値（CPU / Memory / Disk）やログレベル、環境（development / paper_trading / live）の検証
  - 環境値の保護（protected set）を考慮した .env 上書き挙動を実装

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar がない場合は曜日ベース（週末除外）でフォールバックする一貫した振る舞いを実装
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存（バックフィル、健全性チェックを含む）
  - pipeline / etl / ETLResult:
    - ETLResult データクラスで ETL 実行結果を集約（品質問題・エラー一覧を含む）
    - ETL パイプライン方針・ユーティリティを実装（差分取得、backfill、品質チェックフロー等）
    - DuckDB を前提としたテーブル存在チェックや最終日取得ユーティリティを実装
  - jquants_client を介した外部取得・保存ロジックを想定した統合（実装は jquants_client 側に依存）

- ニュース NLP / 市場レジーム判定（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとに記事を束ね、OpenAI（gpt-4o-mini）の JSON Mode を使って一括センチメント評価を行う機能を実装
    - チャンク処理（1 API 呼び出しで最大 20 銘柄）と、トークン肥大化対策（記事数/文字数制限）を導入
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ処理を実装
    - レスポンスの堅牢なバリデーション（JSON抽出、results キー、コード検証、数値変換、±1.0 クリップ）
    - DB への書き込みは部分失敗に備え、先に対象コードを DELETE → INSERT（個別 executemany）して既存スコアの保護
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ計算）を提供
    - テスト用に OpenAI API 呼び出し箇所を差し替え可能（_call_openai_api の patch を想定）
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装
    - ma200_ratio 計算、マクロ記事の抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフを採用
    - OpenAI クライアント呼び出し箇所もテスト差し替えを容易に設計
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照せず、SQL の date < target_date 条件などで安全に処理

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）等のファクター計算関数を実装
    - DuckDB のウィンドウ関数を活用した効率的な SQL 実装（欠損データ時の None ハンドリング含む）
    - 結果は (date, code) をキーとする dict のリストとして返却
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: LEAD を用いた任意ホライズンの一括計算（horizons の検証あり）
    - IC（calc_ic）: Spearman ランク相関（ランクは同順位平均）を実装。データ不足時は None を返す
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリのみで算出
    - rank 関数: 丸めを入れて ties を正しく扱うランク付け実装

- DuckDB を中心とした設計
  - 多くの処理（news/price/financials/calendar/research）は DuckDB 接続を受け取り SQL と Python を組み合わせて実行
  - DuckDB バージョン互換性の配慮（executemany 空リスト回避、リストバインドの回避など）

- ロギングと観察性
  - 各モジュールで詳細な logging を追加（info/debug/warning）し、異常時の原因追跡を容易にしている

Other notable behaviors / design decisions
- ルックアヘッドバイアス防止を徹底:
  - target_date ベースのウィンドウ計算、SQL の date < / BETWEEN 範囲で将来データを使用しない設計
- API キー解決:
  - 各 AI 関数は api_key 引数を受け取り、None なら環境変数 OPENAI_API_KEY を参照（未設定時は ValueError）
- フェイルセーフ:
  - OpenAI や外部 API の失敗は可能な範囲でフォールバックして処理継続（例: macro_sentiment=0.0、スコア未取得ならスキップ）
- テストフレンドリー:
  - _call_openai_api 等の内部呼び出しを簡単にモック可能に設計

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 該当なし

Removed
- 該当なし

Security
- 機密情報（API キー等）は Settings 経由で管理することを想定しており、.env の自動読み込みでは OS 環境変数を protected として上書きを防ぐ仕組みを追加

注意事項（利用者へのメモ）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings で必須扱い（未設定時は ValueError）
  - OpenAI を使う機能を利用する場合は OPENAI_API_KEY を環境変数か関数引数で設定する必要あり
- .env の自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能
- DuckDB を用いてデータベース操作を行うため、ローカルに DuckDB を準備しておくこと
- AI 呼び出しは API 利用料が発生します。バッチ処理で大量に呼ぶ想定のため、コスト管理に注意してください

今後の改善候補（推測）
- strategy / execution / monitoring サブパッケージの具現化（現状は公開されているが実装が別途必要）
- より細かい品質チェックルールや自動アラート統合
- テストカバレッジ整備（モックを用いた E2E テスト・性能テスト）
- OpenAI の利用を抽象化して複数モデルやローカル LLM に切り替えやすくするラッパー層

--- 

この CHANGELOG はソースコードの実装から推測して作成しています。必要があれば日付や文言を実際のリリース履歴に合わせて調整してください。