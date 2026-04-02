Keep a Changelog 準拠の CHANGELOG.md（日本語）
=======================================

このファイルはリリースノート形式で変更点・導入機能・既知の問題を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-02
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」パッケージの基礎機能を実装しました。

追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"、主要サブパッケージを __all__ に公開）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env 行のパーサ実装：コメント、export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープに対応。
  - Settings クラスを提供（settings オブジェクト経由で利用）。
    - 必須環境変数チェック（_require）を実装。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）/ログレベルの取得と検証を実装。
    - デフォルト値や型変換（Path, float）を含む。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストをまとめ、OpenAI（gpt-4o-mini）でバッチ評価し ai_scores に書き込む処理。
    - 時間ウィンドウ（前日15:00 JST～当日08:30 JST = UTC ベースの [window_start, window_end)）の計算関数 calc_news_window を提供。
    - バッチサイズ、記事数・文字数上限、JSON Mode 利用、レスポンス検証、スコアクリッピング（±1.0）を実装。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフを実装。失敗はスキップして継続（フェイルセーフ）。
    - レスポンスバリデーションで未知コードの無視や数値検証を行う。
    - score_news API を公開（DuckDB 接続と target_date を受け取る）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、再試行ポリシー、API失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを防ぐ設計（date 比較や target_date 未満のデータ利用など）。
    - score_regime API を公開（DuckDB 接続と target_date を受け取る）。
  - ai/__init__.py で score_news を再エクスポート。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定（is_trading_day）、SQ判定、前後の営業日取得（next_trading_day / prev_trading_day）、期間内の営業日列挙（get_trading_days）を実装。
    - DB データがない場合は曜日ベースで土日を休日扱いするフォールバックを持つ。DB とフォールバックの組合せで一貫した挙動を確保。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装（バックフィル・健全性チェック付き）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得/保存件数、品質問題、エラー一覧などを保持）。
    - 差分取得、保存（jquants_client の save_* を使用した冪等保存）、品質チェックの考え方を反映した設計。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
  - jquants_client との連携ポイント（fetch/save 呼び出しを想定）。
- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー系ファクターを計算する関数を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA 乖離率）を計算。
    - calc_volatility: 20日 ATR / ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily から PER / ROE を計算（EPS が 0 or NULL の場合は None）。
  - feature_exploration: 将来リターン calc_forward_returns、IC（Spearman ρ）calc_ic、rank、factor_summary を実装。
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得可能（入力検証あり）。
    - calc_ic: ファクターと将来リターンのランク相関を計算（有効レコードが 3 未満の場合は None を返す）。
    - rank: 同順位は平均ランクで扱う実装。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
  - research.__init__ で主要関数を再エクスポート。
- その他
  - DuckDB を主要なデータストアとして想定し、各モジュールが DuckDB 接続オブジェクトを受ける設計。
  - ロギング、詳細なデバッグ/警告ログ出力を多用して運用時の可観測性を高める。

変更 (Changed)
- 設計方針の明示化（ルックアヘッドバイアス防止、フェイルセーフ、DB 優先だがフォールバックあり等）。
- OpenAI 呼び出しに対する堅牢なリトライ戦略と、テスト時のパッチ差替え容易性を考慮した _call_openai_api の分離実装。

修正 (Fixed)
- （初回リリースのため、主に実装済みの安全対策・入力検証を反映。既知のランタイムバグ修正履歴は該当なし。）

削除 (Removed)
- なし

既知の問題 (Known Issues)
- data.pipeline._get_max_date の実装が配布済コード断片上で途中で切れている（"return date.fro" で終端）。配布元ソースが途中で切れている場合、当該関数は正しく動作しません。実際の利用時には該当箇所を最終的に正しい日付変換（例: date.fromisoformat 等）で補完する必要があります。
- OpenAI API キー未設定時、score_news / score_regime は ValueError を投げます（呼び出し側でキー注入または環境変数 OPENAI_API_KEY を設定してください）。
- DuckDB バインド時の互換性注意:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）の挙動を考慮して空チェックを実装しているが、利用する DuckDB のバージョンに応じてテストが必要です。

移行ノート / 運用メモ (Migration / Operational notes)
- 環境変数（主要）
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI: OPENAI_API_KEY（score_news / score_regime 呼び出し時）
  - その他: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL
- .env の自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml があるディレクトリ）。パッケージ配布後に想定どおり動作させる場合は環境変数を明示的に設定することを推奨します。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で利用）。
- OpenAI 呼び出しは gpt-4o-mini を前提に JSON Mode を用いています。API のバージョンやレスポンス仕様変更に注意してください。
- データベーススキーマ: モジュールは prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを参照します。最初に適切なスキーマを用意してください。

開発者向けメモ
- テスト容易性のため、OpenAI 呼び出し関数は各モジュール内で別実装として定義されており、unittest.mock.patch で差し替えて単体テストが可能です。
- ルックアヘッドバイアス防止のため、どの関数も datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計です。

ライセンス / 著作権
- リポジトリのライセンス・著作権情報は別ファイルを参照してください。

補足
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートはリポジトリのコミット履歴に基づいて作成することを推奨します。