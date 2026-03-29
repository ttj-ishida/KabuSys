Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

フォーマット
-----------
リリースは日付付きの見出しで記録し、カテゴリは一般的な分類（Added, Changed, Fixed, Deprecated, Removed, Security 等）を使用します。

Unreleased
----------
（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-29
-------------------

Added
-----
- パッケージ初期公開（kabusys v0.1.0）。
- 基本パッケージ構成の追加:
  - kabusys.config: .env / 環境変数読み込み、プロジェクトルート自動検出、厳格なパースロジック、必須環境変数チェックを提供。
    - 自動ロード順: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ: export 文、クォート（シングル/ダブル）やバックスラッシュエスケープ、行内コメントの取り扱いに対応。
    - Settings クラス: J-Quants / kabu / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベル等のプロパティを提供。無効な値は ValueError で通知。
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でバッチ解析して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン過膨張対策（記事数、文字数 トリム）、レスポンス検証、スコアクリップ（±1.0）。
    - ネットワーク/429/5xx に対する指数バックオフリトライ、失敗時は個別チャンクをスキップするフェイルセーフ設計。
    - テスト用に _call_openai_api の差し替えが可能。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を算出し market_regime に保存する機能。
    - prices_daily と raw_news を利用、LLM 呼び出しは OpenAI client を利用。API エラーやパース失敗時は macro_sentiment=0.0 で継続。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクション/ROLLBACK 処理。
  - kabusys.data:
    - calendar_management: market_calendar を使った営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と calendar_update_job（J-Quants から差分取得し保存）を実装。DB が空の場合は曜日ベースのフォールバックを採用。
    - pipeline / etl: ETLResult データクラス、差分取得・バックフィル方針、品質チェック（quality モジュールを利用）を想定した ETL パイプラインの骨組みを提供。DuckDB に依存。
    - etl モジュールは ETLResult を再エクスポート。
  - kabusys.research:
    - factor_research: モメンタム（1/3/6M、ma200乖離）、ボラティリティ（20 日 ATR、流動性）、バリュー（PER, ROE）等のファクター計算を実装。prices_daily / raw_financials のみを参照。
    - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman のランク相関）、rank / factor_summary といった統計ユーティリティを実装。
    - kabusys.data.stats の zscore_normalize を re-export。
- ロギングと詳細なデバッグメッセージを各モジュールに追加（処理状況・警告・エラーの出力）。

Changed
-------
- （初回公開のため変更履歴なし）

Fixed
-----
- （初回公開のため修正履歴なし）

Security
--------
- 環境依存の機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）は Settings を通じ必須チェックを実施。未設定時は ValueError を発生させ、安全性を確保。
- .env の自動読込時に OS 環境変数を上書きしないデフォルト挙動（必要時 .env.local で上書き）が採用され、意図しない上書きを防止。

Notes / 実装上の重要点（利用者向け）
---------------------------------
- ルックアヘッドバイアス防止:
  - score_news / score_regime / 各種 research 関数はいずれも datetime.today()/date.today() を直接参照せず、引数の target_date に基づいてウィンドウ計算を行います。実運用でもテストでも予期しない未来データの参照を避けられます。
- OpenAI 呼び出し:
  - API キーは関数引数で注入可能（テスト時に外部依存を排除しやすい）。
  - テスト用に内部の _call_openai_api を unittest.mock.patch で差し替え可能。
  - レスポンスは JSON モード前提だが、余剰テキストが混ざる場合に外側の {} を抽出して復元する等、パース耐性を高めています。
- DuckDB に関する注意:
  - DuckDB 0.10 系での executemany に空リストを渡せない制約に対応するため、空チェックを行ってから executemany を呼び出しています。
  - 一部 SQL で ROW_NUMBER / WINDOW を多用しているため、prices_daily / raw_financials / raw_news 等のスキーマおよびデータ整合性が前提です。
- DB 書き込みは冪等を意識:
  - ai_scores / market_regime 等は既存行を DELETE してから INSERT する実装で、部分失敗時に他コードの既存データを保護する設計になっています。
- フォールバック挙動:
  - カレンダー情報が未取得または不完全な場合、曜日（平日=営業日）ベースでのフォールバックを行い、next_trading_day / prev_trading_day / get_trading_days で一貫した結果を返します。
- バックフィルと健全性チェック:
  - calendar_update_job / ETL はバックフィル日数を取り、API 側の後出し修正（訂正）を取り込めるようになっています。極端な将来日が検出された場合は処理をスキップして警告を出します。

Migration / 初期セットアップ
---------------------------
- 必須環境変数:
  - OPENAI_API_KEY（score_news / score_regime 実行時）
  - JQUANTS_REFRESH_TOKEN（J-Quants クライアント利用時）
  - KABU_API_PASSWORD（kabu API 利用時）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知機能利用時）
- データベース（DuckDB）上に次のテーブルが想定されます:
  - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime, （その他 ETL が想定するテーブル）。
- .env.example を参照して .env を作成してください。自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。必要に応じ KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。
- テスト実行時は OpenAI の実際の API 呼び出しをモックしてください（_call_openai_api の差し替え）。

Known limitations / TODO（今後の改善余地）
----------------------------------------
- 一部機能は外部品質チェックモジュール（kabusys.data.quality）に依存する記述だが、その実体の導入/実装が必要。
- PBR・配当利回り等のバリューファクターは未実装（calc_value 参照の通り今後の追加予定）。
- ETL の具体的な pipeline 実行フロー（差分計算 -> API 呼び出し -> save_*）のラッパー関数は骨組みのみで、運用ジョブの実装が必要。
- OpenAI レスポンスのスキーマ依存性を減らすための追加検証やリトライ方針の細分化は今後検討の余地あり。

Authors
-------
- 初回実装（kabusys v0.1.0）

謝辞・注意
---------
- この CHANGELOG はソースコードから推測して作成したものであり、実際のリリースノートとは差異がある可能性があります。実運用リリース時には実装差分・マイグレーション手順を必ず確認してください。