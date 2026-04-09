以下は、提示されたコードベースから推測して作成した CHANGELOG.md（Keep a Changelog 準拠）です。実装内容・設計意図はソースコードのコメント・定数・関数名等に基づいて推測しています。

CHANGELOG.md
=============
すべての重要な変更は SemVer に従い、本ファイルは Keep a Changelog のフォーマットに準拠します。

[0.1.0] - 2026-04-09
--------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。
  - __all__ に主要モジュールを公開 (data, strategy, execution, monitoring)。

- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: export 句対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理など細かなパース仕様をサポート。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、J-Quants / kabuステーション / LINE / DB /監視 /システム関連設定をプロパティで提供。
    - 必須項目取得関数 _require (未設定時は ValueError を送出)。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
    - KABUSYS_ENV, LOG_LEVEL 等の許容値チェック。
    - DuckDB/SQLite のデフォルトパス、PID/KILL フラグ、リソース閾値等のデフォルトを設定。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄候補選定 (portfolio_builder)
    - select_candidates: スコア降順、同点時は signal_rank でタイブレーク。
    - calc_equal_weights, calc_score_weights: 等金額配分/スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - リスク調整 (risk_adjustment)
    - apply_sector_cap: セクター毎の既存エクスポージャが閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数（未定義レジームは 1.0 でフォールバック、警告ログ）。
  - 株数決定・単元処理 (position_sizing)
    - calc_position_sizes: allocation_method に応じて買付株数を算出（risk_based, equal, score をサポート）。
    - リスクベース計算（risk_pct, stop_loss_pct）・1銘柄上限・lot_size（単元）・手数料/スリッページの cost_buffer を考慮した aggregate cap スケーリングと残差配分ロジックを実装。
    - 価格欠損や非正数価格の銘柄を安全にスキップするログ出力を含む。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200 乖離の計算（必要データ不足時は None）。
    - calc_volatility: 20日 ATR（true_range 処理）、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算（EPS 欠損時の取り扱い、PBR 等は未実装）。
    - DuckDB を使った SQL + ウィンドウ関数中心の実装。
  - 特徴量探索 / 統計 (feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（入力検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクで処理、丸め誤差対策に round(v, 12) を使用。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージ __init__ で zscore_normalize（kabusys.data.stats 由来）を再エクスポート。

- AI / NLP (kabusys.ai)
  - ニュースセンチメント (ai.news_nlp)
    - calc_news_window: target_date に対するニュースウィンドウ（JST を考慮し UTC に変換）を提供。
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄毎にセンチメントを評価して ai_scores に書き込み。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄/リクエスト）、記事数/文字数上限、レスポンス検証、スコアの ±1.0 クリップ、DuckDB への冪等書き込み（DELETE → INSERT）を実装。
      - OpenAI 呼び出しに対するリトライ（429/ネットワーク/5xx 等）とエラーハンドリング、部分失敗時の保護ロジック（成功したコードのみ更新）。
    - API クライアント呼び出し部分は _call_openai_api を分離（テスト用に差し替え可能）。
  - レジーム判定 (ai.regime_detector)
    - score_regime: ETF 1321 の ma200 乖離 (過去 200 日) とマクロニュースの LLM センチメントを合成して market_regime を判定・DB 書き込み。
      - ma200 のデータ不足時は中立 (1.0) でフォールバック。
      - マクロキーワードで raw_news のタイトルを抽出（最大 件数制限あり）、LLM 呼び出しはリトライとフォールバック（失敗時 macro_sentiment=0.0）。
      - レジームスコアの合成係数（MA: 70%、マクロ: 30%）やしきい値に基づく 'bull' / 'neutral' / 'bear' 判定。
    - news_nlp.calc_news_window を再利用し、OpenAI 呼び出しは局所実装（モジュール分離）。

- 監視ログ永続化 (kabusys.monitoring)
  - monitoring_db.init_monitoring_db: SQLite 用の監視 DB スキーマ作成（冪等）。少なくとも system_status / trade_logs / positions / risk_logs 等のテーブルとインデックス生成スクリプトを実装。
  - ビジネスロジックを持たない永続化レイヤーとしての位置付け。

Changed
- 初期リリースのため該当なし（新規導入）。

Fixed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし（ただし OpenAI API キーは引数または環境変数 OPENAI_API_KEY で受け取り、未設定時は明示的にエラーを出す実装。機密情報の扱いに注意）。

Notes / Limitations（コードから推測される既知事項）
- DuckDB / SQLite スキーマや外部テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）への依存がある。事前に該当テーブルとデータを用意する必要あり。
- OpenAI（gpt-4o-mini）依存機能はネットワークや API 仕様に影響を受ける。テスト用に API 呼び出しの差し替え可能な設計になっている。
- price 欠損時の取り扱いやフォールバック価格未実装（apply_sector_cap の TODO、position_sizing の price チェック等に記載）。将来的な改善余地あり。
- 一部のユーティリティ（例: zscore_normalize）は別モジュール（kabusys.data.stats）に依存しているため、併せて実装が必要。

今後の改善提案（コードからの推測）
- 銘柄別 lot_size を考慮するための拡張（現状はグローバルな lot_size）。
- 価格欠損時のフォールバック（前日終値や取得原価）導入。
- ai モジュールでの応答スキーマ検証強化とメタ情報のログ記録。
- DuckDB の executemany 周りの互換性を踏まえたテストケース整備。

--- 
（注）本 CHANGELOG は提供されたソースコードのコメント・実装・定数・関数名等から推測して作成しています。実際のリリースノートや履歴が存在する場合はそちらを優先してください。