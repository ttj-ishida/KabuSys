# CHANGELOG

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、このCHANGELOGは現行コードベース（バージョン 0.1.0）から推測して作成した初期リリースの記録です。

## [0.1.0] - 2026-03-29

Added
- パッケージ初期公開
  - パッケージメタ情報: `kabusys.__init__` にてバージョン `0.1.0` を設定し、主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定/ロード機能
  - `kabusys.config.Settings` クラスを導入し、環境変数からアプリケーション設定を取得するプロパティ群を提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル判定等）。
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` で検出）。読み込み順は OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - .env パーサは以下をサポート/考慮:
    - `export KEY=val` 形式
    - シングル/ダブルクォートで囲まれた値（バックスラッシュエスケープ処理）
    - インラインコメントの扱い（クォートなしの `#` は前が空白/タブの場合のみコメントとみなす）
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）をサポート。
  - 環境変数の必須チェック時に分かりやすいエラーメッセージを出力する `_require` を提供。
  - `KABUSYS_ENV` と `LOG_LEVEL` の許容値バリデーションを実装（不正値時は ValueError）。

- AI モジュール（OpenAI を利用したニュース解析・レジーム判定）
  - `kabusys.ai.news_nlp.score_news`
    - raw_news / news_symbols テーブルから指定ウィンドウ（JST: 前日15:00〜当日08:30）内の記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - チャンク処理（デフォルト最大 20 銘柄/チャンク）および銘柄内トリム（最大記事数・最大文字数）を実装してトークン肥大化を抑制。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライを実装。フェールセーフとしてAPI失敗時は該当チャンクをスキップして他銘柄処理を継続。
    - レスポンス検証ロジックを実装し、不正なレスポンスはログ出力の上で無視（安全側の挙動）。
    - DuckDB へは冪等的に書き込み（対象コードのみ DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易性のため、OpenAI 呼び出し部分はモジュール内で差し替え可能（patch可能）に実装。
  - `kabusys.ai.regime_detector.score_regime`
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定・保存。
    - MA200 の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はキーワードマッチベース。記事がない場合は LLM 呼び出しをスキップし macro_sentiment=0.0 を使用。
    - OpenAI 呼び出しに対するリトライ／エラー処理（RateLimit/接続/タイムアウト/5xx の取り扱い）を備え、最終的に失敗した場合は macro_sentiment を 0 にフォールバック。
    - 計算結果は `market_regime` テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時はROLLBACKを試行）。

- データ基盤（DuckDB を利用した ETL / カレンダー等）
  - `kabusys.data.pipeline.ETLResult`
    - ETL 実行結果の dataclass を提供。フェッチ/保存件数、品質チェック結果、エラー一覧などを保持し、辞書化 (to_dict) して監査ログなどで利用可能。
  - `kabusys.data.pipeline`（ETLパイプライン）
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。API 取得は jquants_client を利用し、保存は idempotent（ON CONFLICT / save_* 呼び出し）を想定。
  - `kabusys.data.calendar_management`
    - JPX マーケットカレンダー管理を実装。
      - 営業日判定 API: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - market_calendar テーブルが未取得時は曜日ベースでフォールバック（平日を営業日とみなす）。
      - 夜間バッチ job `calendar_update_job` を提供し、J-Quants から差分取得して冪等保存（バックフィル、健全性チェックを含む）。
    - 検索上限やサニティチェック（最大探索日数 / 将来日付の異常検出）を設計に組み込み。

- リサーチ / ファクター分析
  - `kabusys.research.factor_research`
    - モメンタム、ボラティリティ（ATR/出来高等）、バリュー（PER/ROE）の計算関数を提供:
      - calc_momentum: 1M/3M/6M リターン、ma200乖離を計算（データ不足時は None）
      - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率を計算
      - calc_value: raw_financials と prices を組み合わせて PER/ROE を算出（直近報告データを target_date 以前で取得）
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、外部 API には依存しない設計。
  - `kabusys.research.feature_exploration`
    - 将来リターン算出: calc_forward_returns（任意ホライズン、入力検証付き）
    - IC（スピアマン ρ）計算: calc_ic（ランク相関）
    - ランク変換: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - 外部ライブラリ非依存で純粋に標準ライブラリ + SQL（DuckDB）での実装。

- その他の品質・設計上の配慮
  - ルックアヘッドバイアス防止: AI モジュールやリサーチ系関数は内部で datetime.today()/date.today() を参照せず、明示的な target_date に依存する実装。
  - DuckDB との互換性考慮: executemany の空リスト回避、日付型処理の互換性、安全な SQL 生成などを考慮。
  - ロギング: 各主要処理で詳細な info/debug/warning を出力するよう設計（フェイルセーフ時や変則値検出時にログが残る）。
  - テスト容易性: OpenAI 呼び出しや内部ユーティリティの差し替え（mock）を想定した実装。

Fixed
- 初期リリースにつき該当なし（実装時に既知の安全策・フォールバックを多数導入）。

Changed
- 初期リリースにつき該当なし。

Removed
- 初期リリースにつき該当なし。

Notes / 既知の制約
- OpenAI クライアント（gpt-4o-mini）利用部分は API キーが必要。api_key 引数で注入するか環境変数 `OPENAI_API_KEY` を設定する必要あり（未設定時は ValueError を送出）。
- 一部のテーブル（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, news_symbols 等）は DuckDB 上に存在することが前提。テーブル未作成時の挙動は関数ドキュメントを参照。
- 現時点では Strategy / Execution / Monitoring の具体実装は公開モジュール名のみ宣言（__all__）されているが、本CHANGELOGは現行ファイルに基づく初期機能群を記載。

--- 

今後のリリースでは、API の拡張、パフォーマンス改善、追加の品質チェックルール、より細かいモニタリング・アラート機能などを予定しています。