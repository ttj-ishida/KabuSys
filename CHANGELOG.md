Keep a Changelog
=================

すべての重要な変更はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
------------

- （今後の変更はここに記載）

0.1.0 - 2026-03-29
------------------

初回リリース。日本株自動売買プラットフォームの基礎モジュール群を追加します。
以下はソースコードから推測してまとめた「注目すべき追加機能／設計方針／制約」です。

Added
- パッケージ基礎
  - kabusys パッケージ公開（__version__ = 0.1.0）。モジュール群: data, strategy, execution, monitoring を公開。

- 設定/環境変数管理（kabusys.config）
  - .env/.env.local の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能（テスト用途想定）。
  - .env パーサーで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行中コメントの取り扱いなどをサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス等の設定をプロパティ経由で取得。
  - 必須環境変数未設定時は ValueError を発生させる _require を用意。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）、is_live / is_paper / is_dev の簡易判定を提供。

- AI（ニュースNLP・レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で計算。
    - バッチ処理（最大20銘柄/チャンク）、記事最大数/文字数制限、リトライ（429・ネットワーク断・5xx の指数バックオフ）やレスポンスの厳密なバリデーションを備える。
    - APIキーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - フェイルセーフ：API失敗やパース失敗時は該当チャンクをスキップして他を継続。最終的に取得した銘柄数を返却。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を決定し market_regime テーブルに冪等書き込みを行う機能を追加。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を評価、スコア合成と閾値判定を実装。
    - API 呼び出しのリトライ、API 失敗時は macro_sentiment=0.0 のフォールバック（例外を投げず継続）とするフェイルセーフ実装。
    - 日付の扱いはルックアヘッドバイアスを避ける設計（datetime.today() を直接参照しない、prices_daily は target_date 未満のデータのみ使用）。

- データ処理（kabusys.data）
  - calendar_management
    - JPXカレンダーを管理する market_calendar の読み書き／判定ユーティリティを実装（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB にカレンダーがない場合は曜日ベース（土日休）でフォールバックする一貫した挙動。
    - calendar_update_job を提供し J-Quants API から差分取得 → 保存（バックフィルや健全性チェック付き）するナイトジョブを実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分取得・バックフィル・保存・品質チェックの流れを想定した ETL モジュールの基礎を実装（jquants_client / quality モジュールと連携する設計）。
    - DuckDB を用いた最終取得日の判定、テーブル存在チェック等のユーティリティあり。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性（20日平均売買代金、出来高比）およびバリュー（PER、ROE）計算を DuckDB を使って実装。
    - 返り値は (date, code) をキーとする dict のリスト。データ不足時の扱い（None）を明示。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary（count/mean/std/min/max/median）などの統計解析ユーティリティを追加。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する設計。

Design / 安全性 / その他実装上の特徴
- ルックアヘッドバイアス回避: 多くの関数が datetime.today()/date.today() を直接参照しない（target_date を引数で受ける）。
- DB 書き込みは冪等性を考慮（BEGIN/DELETE/INSERT/COMMIT あるいは executemany を用いた置換）している。
- OpenAI 呼び出しは JSON モード利用とレスポンス検証を行い、パース失敗や想定外の出力に対して堅牢に対処。
- DuckDB 互換性を考慮（executemany の空リスト回避や date 型の取り扱いヘルパーなど）。

Known limitations / 注意事項
- OpenAI 連携:
  - OpenAI API キー (OPENAI_API_KEY) が必須（関数引数で注入可能）。未設定時は ValueError。
  - 使用モデルは gpt-4o-mini を想定。API 利用に伴うコストとレイテンシに注意。
- DB スキーマ期待値:
  - raw_news, news_symbols, ai_scores, prices_daily, raw_financials, market_calendar, market_regime などのテーブル構造を前提としている（本実装ではスキーマ定義は含まれないため、環境に応じたテーブル準備が必要）。
- 依存:
  - duckdb パッケージ、openai（OpenAI Python SDK）等が必要。
- パフォーマンス:
  - ニュース解析は記事集約・トリム・バッチ送信を行うが、多数銘柄／長文記事の環境ではトークン・API呼び出し回数が多くなる。運用時はバッチサイズや文字数閾値の調整を検討すること。
- テスト向けフック:
  - OpenAI 呼び出し箇所はテストでモックしやすい（モジュール内の _call_openai_api を patch）。

Migration / 利用開始ガイド（簡易）
- .env/.env.local に必要な環境変数を設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）。
- DuckDB ファイルを準備し、期待されるテーブルスキーマ（prices_daily, raw_news...）を作成する。
- OpenAI を利用する機能（score_news, score_regime）を呼ぶ際は api_key 引数か環境変数 OPENAI_API_KEY を設定。
- calendar_update_job や ETL パイプラインは jquants_client / quality 実装と連携して動作する想定。

Fixed
- （初版のため該当なし）

Changed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数の取り扱いに注意（APIキー等は漏洩しないよう .env の管理を徹底）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを止めることが可能。

補足
- 本 CHANGELOG は提示されたソースコードをもとに推測して記載しています。実際のリリースノートや運用指示はソースコードの更新履歴・運用ポリシーに基づき適宜補完してください。