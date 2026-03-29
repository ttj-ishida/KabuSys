CHANGELOG
=========

すべての重要な変更は本ファイルに記録します。このファイルは「Keep a Changelog」形式に準拠しています。
バージョン番号は package の __version__（src/kabusys/__init__.py）に合わせています。

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初回公開相当の実装を追加。
  - 基本パッケージ定義
    - kabusys.__init__ にて __version__ を "0.1.0" として公開。主要サブパッケージ（data, research, ai, ...）を __all__ でエクスポート。
  - 設定管理（kabusys.config）
    - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local 読み込みの優先度および OS 環境変数保護（protected keys）。
    - export KEY=val 形式やクォート付き値、コメント付き行等に対応するパーサ実装。
    - 環境変数必須チェック（_require）や Settings クラスを公開（J-Quants / kabu / Slack / DB / 実行環境フラグなどのプロパティを提供）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数をサポート。
  - AI（kabusys.ai）
    - news_nlp モジュール: raw_news と news_symbols を使用して銘柄ごとのニュースを集約、OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価を行い、ai_scores テーブルへ安全に書き込み。
      - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄当たりの最大記事数・最大文字数によるトリム実装。
      - JSON Mode レスポンスのバリデーション、スコアクリップ（±1.0）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
      - レスポンスパース失敗や API エラーはフェイルセーフとしてスキップし、例外を上位へ上げない設計。
      - calc_news_window ユーティリティ（JST ウィンドウ → UTC naive datetime 変換）。
    - regime_detector モジュール: ETF 1321（日経225連動）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
      - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロキーワード検索、OpenAI 呼び出しとリトライ、スコア合成・閾値判定、DB トランザクション処理。
      - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
  - Data（kabusys.data）
    - calendar_management: JPX カレンダー管理用ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間バッチ更新 job（calendar_update_job）。
      - market_calendar テーブルが未取得の場合の曜日ベース fallback（週末は非営業日）や DB 登録値優先の一貫した判定ロジック、最大探索上限（_MAX_SEARCH_DAYS）による無限ループ防止。
      - calendar_update_job は J-Quants クライアント経由で差分取得し冪等保存、バックフィルと健全性チェックを実装。
    - pipeline / etl: ETLResult データクラスと ETL パイプラインの基本概念を追加（差分取得、保存、品質チェックフローの説明・ユーティリティ）。
      - ETLResult は品質問題やエラー要約を保持し to_dict() による監査データ出力を提供。
    - jquants_client 経由の保存戦略を想定した設計（差分取得、バックフィル、品質チェックの流れ）。
  - Research（kabusys.research）
    - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算（prices_daily / raw_financials を参照）。
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時 None を返す）。
      - calc_volatility: 20日 ATR・相対 ATR、20日平均売買代金・出来高比などを計算（データ不足時 None）。
      - calc_value: raw_financials から最新財務を取り、PER/ROE を計算。
    - feature_exploration: 将来リターン（calc_forward_returns）、IC 計算（calc_ic）、ファクタ統計サマリー（factor_summary）、rank ユーティリティ等を提供。
      - calc_forward_returns は任意ホライズン（horizons）を受け付け、リクエスト検証（正の整数かつ <=252）を実施。
      - calc_ic はスピアマンのランク相関を実装（有効ペア数 < 3 は None を返す）。
      - rank は同順位の平均ランクを返す実装（丸めで ties を安定化）。
  - 共通設計/実装上の方針（ドキュメントとしてコード内に明示）
    - ルックアヘッドバイアス回避のため、datetime.today()/date.today() に依存せず、すべての処理が target_date ベースで deterministic に動作する設計。
    - DuckDB を主要なローカル分析 DB として利用（SQL とウィンドウ関数を多用）。
    - DB への書き込みは冪等化（DELETE→INSERT、トランザクション処理、部分失敗に備えたコード絞込み）を重視。
    - OpenAI 呼び出しは専用ラッパー関数を持ち、テストのため差し替えやすくしている（unittest.mock.patch を想定）。
    - ロギングを多用し、異常時は警告/例外ログを残す。

Security
- OpenAI API キーや Slack トークン、Kabu API パスワード等の機密情報は環境変数経由で取得する設計。必須環境変数が未設定の場合は ValueError を送出して早期検出する。

Notes / 既知の制約
- OpenAI 呼び出し部分は外部 API に依存するため、API 仕様や SDK のバージョン変化（例: status_code の有無）に注意して安全に扱う実装（getattr 等で保守性を高めている）。
- DuckDB の executemany に関する挙動（空リスト不可）を考慮した実装が含まれる。
- 一部の機能（J-Quants クライアント、kabu API 連携、Slack 通知、DB スキーマ定義など）は本コードベースでの利用を想定しているが、実行環境側のセットアップ（.env 作成、DB テーブル作成、API キー準備）が必要。
- calendar_update_job / ETL パイプラインは J-Quants API の呼び出しに依存。API エラー時はジョブは 0 を返す等のフェイルセーフが入っている。

BREAKING CHANGES
- なし（初回リリース）。

Upgrade Notes
- 初回リリースのためアップグレード作業は不要。導入時は .env.example を参考に必要な環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。

--- 
（本CHANGELOGはコードベースの内容から推測して作成しています。実際のリリースノート作成時はリリース手順・マイグレーションや外部依存のバージョンなどを合わせて追記してください。）