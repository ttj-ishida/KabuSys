CHANGELOG
=========
すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

注: 以下は提供されたコードベースから機能・設計意図を推測して作成した初期リリース向けの変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-26
--------------------

Added
^^^^^

- パッケージ基盤
  - 初期リリースとして kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を含む（src/kabusys/__init__.py）。

- 設定管理（kabusys.config）
  - .env/.env.local からの自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 強化された .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - 環境変数の上書き制御（override / protected による OS 環境保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ経由で取得。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の列挙と不正値での例外）。

- データ関連（kabusys.data）
  - calendar_management:
    - market_calendar を基にした営業日・SQ判定ユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数制限による安全設計。
    - calendar_update_job: J-Quants からカレンダーを差分取得して保存するバッチジョブ（バックフィル・健全性チェック含む）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題やエラーの保持、辞書化ユーティリティ）。
    - ETL モジュールにおける差分取得、バックフィル、品質チェックなどの設計方針を反映するユーティリティ関数群（テーブル存在チェック、最大日付取得等）。
  - データ層は DuckDB を想定した実装。一貫して date オブジェクトを使用。

- 研究・リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE の算出（target_date 以前の最新財務データを使用）。
    - SQL ウィンドウ関数を多用し、DuckDB 上で高速に集計する実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル数が不足する場合は None を返す。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - いずれの関数も本番取引 API にアクセスしない設計（分析専用）。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたり記事数と文字数のトリム、JSON Mode 応答のバリデーション、スコアの ±1.0 クリップ。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ + リトライ、非リトライエラーはスキップ。部分成功時に既存データを保護するため DELETE → INSERT の方式で部分置換。
    - OpenAI API 呼び出し箇所はテスト容易性のため差し替え可能（内部 _call_openai_api）。
    - DuckDB executemany の互換性（空リストへの注意）を考慮して実装。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（マクロキーワード一覧）と LLM 評価を行う _score_macro。API 障害時は macro_sentiment=0.0 にフォールバック。
    - レジーム合成時にクリップを行い閾値でラベル付け。
    - OpenAI 呼び出しは外部キー（引数または OPENAI_API_KEY）で解決し、未設定時は ValueError を送出。

Changed
^^^^^^^

- （初期リリースのため該当なし）

Fixed
^^^^^

- （初期リリースのため該当なし）

Security
^^^^^^^^

- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY 経由で解決され、未設定時は明示的にエラーを発生させることで誤動作を防止。
- .env 自動ロード時に既存 OS 環境変数を保護する実装（protected セット）。

Notes / 設計上の重要ポイント
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ルックアヘッドバイアス防止: スコア計算・ウィンドウは内部で date.today()/datetime.today() を参照しない方針。target_date を明示的に受け取る設計。
- フェイルセーフ: OpenAI 等外部 API の失敗はデフォルト値（0.0）やスキップで処理を継続し、致命的な例外でない限り全体処理が止まらないよう配慮。
- DuckDB 互換性: executemany の空パラメータ回避や date 型の取り扱いなど実運用での互換性考慮がなされている。
- DB 書き込みは可能な限り冪等（DELETE/INSERT、BEGIN/COMMIT/ROLLBACK ハンドリング）を採用。
- 外部依存を最小化（分析コードは pandas 等に依存しない）し、テスト容易性を重視した設計（内部 API 呼び出しの差し替えポイントを確保）。

---

過去リリースや将来の変更については、このファイルを更新していきます。追加の詳細やリリースノートの粒度調整（例: モジュール別の細かな変更履歴）をご希望の場合は指示してください。