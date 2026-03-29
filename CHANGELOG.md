KEEP A CHANGELOG 準拠 — 変更履歴
=============================

すべての注目すべき変更をこのファイルで管理します。
このプロジェクトのバージョニングは SemVer を想定しています。

フォーマットの方針:
- 重大な変更はカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに整理します。
- 日付はリリース日を示します。

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0" として公開。
  - 公開サブパッケージ: data, strategy, execution, monitoring（モジュール構成のルートエクスポート）。
- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数経由で設定値を提供（J-Quants / kabuステーション / Slack / DB パス等）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点に探索）。
  - .env ファイルパーサ実装: export プレフィックス、シングル/ダブルクォート、多重エスケープ、インラインコメント処理等に対応する堅牢な _parse_env_line。
  - 自動ロード抑止フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 設定検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値チェック、必須環境変数未設定時は ValueError を発生。
- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news を実装: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - ニュース収集ウィンドウの計算（JST 基準 → UTC 変換）：前日 15:00 JST ～ 当日 08:30 JST（calc_news_window）。
  - バッチ処理とトークン肥大対策: 銘柄毎記事数上限 (_MAX_ARTICLES_PER_STOCK) と文字数上限 (_MAX_CHARS_PER_STOCK)、1 API 呼び出しあたりの最大銘柄数 _BATCH_SIZE。
  - エラー処理/リトライ: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ実装（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
  - レスポンスバリデーション: JSON 抽出・検証、未知コードや非数値スコア除外、±1.0 にクリップ。
  - DB 書き込みは冪等（DELETE → INSERT）かつ部分失敗時に既存スコアを保護する実装。
  - テストフック: _call_openai_api をパッチ可能にしてユニットテスト容易性を確保。
- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime を実装: ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
  - マクロニュース抽出のキーワードリストおよび OpenAI を用いた macro_sentiment 評価（gpt-4o-mini）。
  - フェイルセーフ: API 失敗時は macro_sentiment を 0.0 として継続。
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
- リサーチ（src/kabusys/research/）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。モメンタム・ボラティリティ・バリュー計算を提供。
  - feature_exploration: calc_forward_returns（複数ホライズンの将来リターン取得）、calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（統計要約）を実装。
  - zscore_normalize を data.stats から再エクスポートするインターフェースを準備。
  - すべて DuckDB 接続を受け取り SQL + Python で完結、外部 API やサイドエフェクトなし。
- データ基盤ユーティリティ（src/kabusys/data/）
  - calendar_management: JPX カレンダー管理、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日ロジックと calendar_update_job（J-Quants から差分取得して市場カレンダー更新）を実装。DB データ優先・未登録日は曜日ベースのフォールバックを採用。
  - pipeline: ETLResult データクラス（ETL 実行結果の集約）、ETL パイプラインのユーティリティ（差分取得、保存、品質チェックのラッパー）を実装。
  - etl.py で ETLResult を再エクスポート。
- 共通設計方針（ドキュメント化された実装方針）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部ロジックで直接参照しない設計を徹底（target_date 受け渡しによる決定）。
  - DuckDB を利用した SQL ベースの集約・ウィンドウ計算（互換性考慮のコメントあり）。
  - ロギングと詳細な警告・情報メッセージを多数追加。
  - テスト容易性のための差し替えポイント（_call_openai_api 等）を用意。

Fixed
- DB 操作の互換性対策:
  - DuckDB 0.10 の制約に合わせ、executemany に空リストを渡さないように条件分岐を追加（score_news, pipeline など）。
- API エラー処理の堅牢化:
  - OpenAI API 呼び出しでの 5xx/429/接続断/タイムアウトを想定したリトライ処理とフェイルセーフの実装（マクロ評価失敗時は中立スコア）。
- 日付/型処理の堅牢化:
  - DuckDB から戻る日付型の変換ユーティリティ _to_date を追加して日付比較を安定化。

Changed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- OpenAI / 各種 API キーは環境変数で管理。必須キー未設定時は明示的に ValueError を発生させることで安全性と運用ミスの早期検出を図る。
- .env 自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テスト環境や CI での誤読込みを防止。

Notes / Implementation details
- デフォルトで使用する OpenAI モデルは gpt-4o-mini。JSON mode（response_format）を用いて厳密な JSON 出力を期待する実装。
- news_nlp と regime_detector は同様の LLM 呼び出し機構を持つが、モジュール間のプライベート関数共有は避け、それぞれ独立実装（テストの独立性向上）。
- 各種閾値やウィンドウ（例: MA 200, ATR 20, バッチサイズ 20, スコアクリップ ±1.0 等）は定数化され、ソース内でコメントによる仕様説明が付与されている。
- ETL 結果は ETLResult.to_dict() で品質問題を簡単に監査ログへ出力可能。

将来の計画（参考）
- strategy / execution / monitoring の詳細実装と統合テスト
- ai モジュールの追加改善（LLM プロンプト改善、モデル切替オプション）
- ETL の品質チェック強化とメトリクス露出

参照
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/