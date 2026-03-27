CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" のコア機能を公開。
- パッケージ公開:
  - パッケージルート: kabusys.__version__ == "0.1.0"
  - サブパッケージ公開: data, research, ai, config 等のモジュール群をエクスポート。

- 環境/設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読込（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読込順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読込を無効化可能。
  - .env パーサ実装: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメント処理（クォート有無で挙動を区別）。
  - _load_env_file の override / protected パラメータにより OS 環境変数の保護を実現。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の必須/省略時デフォルト値、検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実施。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode でセンチメント評価を行い、ai_scores テーブルへ書き込み。
  - タイムウィンドウ設計（JST基準）: 前日 15:00 JST ～ 当日 08:30 JST（DBでは UTC ナイーブ datetime を使用）。
  - バッチ処理: 最大 20 銘柄／リクエスト、記事トリム（1銘柄あたり最大 10 記事、最大 3000 文字）。
  - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフとリトライ実装。恒久的な失敗はスキップし例外を投げない（フェイルセーフ）。
  - JSON レスポンスの堅牢なバリデーション（results 配列、code/score の型チェック、未登録コード無視、スコア ±1.0 にクリップ）。
  - テスト容易性: _call_openai_api をテストで差し替え可能（unittest.mock.patch 推奨）。
  - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
  - マクロキーワードによる raw_news フィルタリング実装。LLM（gpt-4o-mini）を JSON モードで呼び出し macro_sentiment を取得。
  - 計算フロー: ma200_ratio の算出（target_date 未満のデータのみ使用でルックアヘッドを防止）→ LLM 評価（記事なし時は呼び出しを行わず macro_sentiment=0）→ 合成スコア clip(-1,1) → ラベル付与 → DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - API のリトライロジックとフェイルセーフ: 失敗時 macro_sentiment=0.0 を用いる。

- データプラットフォーム / ETL（kabusys.data.pipeline, etl）
  - ETLResult データクラスを公開（処理統計・品質問題・エラー一覧・ヘルパーメソッド to_dict）。
  - 差分更新戦略、バックフィル日数、品質チェックのためのユーティリティを用意。
  - DuckDB との互換性確保（テーブル存在確認・最大日付取得ユーティリティ等）。

- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー管理: market_calendar を基に営業日判定、次/前営業日取得、期間の営業日リスト取得、SQ日判定を提供。
  - カレンダー未取得時は曜日（平日）でフォールバックする一貫した挙動。
  - calendar_update_job により J-Quants API から差分取得 → 冪等保存（ON CONFLICT 相当）を行う。直近のバックフィルや健全性チェックを実装。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算。
  - feature_exploration: 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、factor_summary（count/mean/std/min/max/median）、rank（平均ランク・同順位は平均）。
  - 設計方針により、本モジュールは外部取引 API や本番口座にアクセスしない。

Changed
- N/A（初回リリースのため履歴なし）。

Fixed
- N/A（初回リリースのため履歴なし）。

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数の取り扱いに注意:
  - 必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings で取得時に未設定なら ValueError を送出。
  - .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト用途）。

開発者向け注記
- ルックアヘッドバイアス対策: いずれのスコア計算/ETL でも datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- DuckDB executemany に対する互換性処理（空リストチェックなど）を行っているため、DuckDB バージョン固有の挙動に配慮済み。
- OpenAI 呼び出し部分は各モジュール内で独立した _call_openai_api を実装しており、モジュール間で内部関数を共有しない（テストでの差し替えを想定）。
- ロギングを適切に配置し、API のリトライ・フェイルセーフ動作時に WARN/INFO/DEBUG を出力。

今後の予定（非確定）
- PBR、配当利回りなどバリューファクターの拡張。
- モデルの切替やプロンプト改善、LLM出力のさらなる堅牢化。
- ETL/品質チェックの細分化とアラート連携（Slack 等）。

---