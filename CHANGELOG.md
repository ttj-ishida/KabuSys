Keep a Changelog準拠の CHANGELOG.md（日本語）。コード内容から推測して記載しています。

注意: 記載内容は提供されたソースコードに基づく推測であり、実際のコミット履歴とは異なる場合があります。

Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
---------

- ドキュメントや内部 TODO に基づく将来的な改善メモを追加予定:
  - 銘柄ごとの単元株（lot_size）を銘柄マスタから読み込めるようにする拡張案
  - position_sizing の price 欠損時のフォールバック（前日終値や取得原価）の実装
  - DuckDB / SQLite 周りの互換性向上やエッジケースの追加テスト

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ基盤
  - パッケージ初期バージョンを導入（__version__ = 0.1.0）。
  - モジュールのエクスポート定義を追加（kabusys.research / kabusys.portfolio / kabusys.ai などの公開 API）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local ファイルの自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロード抑止フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、各種設定をプロパティ経由で取得（必須キーの検査、既定値、型変換、値検証を含む）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL 値検査、PAPER_FILL_MODE 値検査等を実装。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - 銘柄候補選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
  - 重み計算:
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコアが 0 の場合は等金額へフォールバック）
  - リスク調整:
    - apply_sector_cap（既存保有セクター比率が閾値を超える場合、新規候補を除外。unknown セクターは除外対象外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数: bull/neutral/bear をマッピング、未知レジームはフォールバック）
  - ポジションサイズ計算:
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート。単元丸め、per-position / aggregate cap、cost_buffer を考慮したスケーリングロジック、残差分の lot 単位での再配分を実装）

- リサーチ（src/kabusys/research/）
  - ファクター計算（duckdb を想定）:
    - calc_momentum（1m/3m/6m リターン、MA200 乖離。データ不足時は None を返す設計）
    - calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）
    - calc_value（latest raw_financials と price を組み合わせて PER/ROE を計算）
  - 特徴量解析ユーティリティ:
    - calc_forward_returns（指定ホライズンの将来リターンを一括 SQL で取得）
    - calc_ic（スピアマンのランク相関による IC 計算。有効レコードが 3 未満なら None）
    - rank（同順位は平均ランクでの処理、浮動小数丸めを考慮）
    - factor_summary（count/mean/std/min/max/median を算出）
  - 設計方針として外部 API へアクセスせず DuckDB のみ参照する旨を明記（ルックアヘッドバイアス回避の考慮含む）。

- AI 関連（src/kabusys/ai/）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む機能（score_news）。
    - タイムウィンドウの算出（JST ベース→UTC 変換）。lookahead を避ける設計（target_date に依存）。
    - 銘柄単位で記事集約、チャンク分割（最大 _BATCH_SIZE）してバッチ API 呼び出し。
    - JSON Mode を利用したレスポンスバリデーション（results 配列の必須性、code/score の検査、クリッピング ±1.0）。
    - 再試行戦略（429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフ）とフェイルセーフ（API 失敗時は該当チャンクをスキップ）。
    - DuckDB 書き込みは部分失敗に備え、対象 code に限定した DELETE → INSERT の冪等処理を採用。executemany の空リスト対応の注意書きあり。
    - テスト用フック: _call_openai_api をパッチ可能（unittest.mock で差し替え想定）。

  - レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定（score_regime）。
    - マクロニュースはマクロキーワードでフィルタ。タイトル最大件数で集計。
    - API 呼び出しの再試行とフォールバック（失敗時は macro_sentiment=0.0）。
    - DuckDB への冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - news_nlp との連携はあるが、OpenAI 呼び出し関数はモジュールごとに独立実装（テストの独立性確保）。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた監視ログ永続化層を実装（init_monitoring_db により system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等で作成）。

Changed
- （初期リリースのため該当なし — 初回追加内容のみ）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーの取り扱いは引数優先 → 環境変数（OPENAI_API_KEY）にフォールバックする設計。未設定時は ValueError を発生させ明示的に失敗させることで無効な API 呼び出しを防止。

Notes / Implementation details
- 研究系 API は外部ネットワークを呼ばない設計（DuckDB 内の prices_daily / raw_financials / raw_news を参照するのみ）。
- ルックアヘッドバイアス対策が各所に明記されている（target_date 未満のみ参照、datetime.today() を参照しない等）。
- ロギングや警告を多用しており、異常系は例外・警告で検知しやすい設計。
- 一部処理に TODO コメントあり（例: price 欠損時のフォールバックや銘柄別 lot_size 管理など）。

過去のバージョン
----------------
- （本リポジトリ提供分は初回リリースのため履歴なし）

--- End of CHANGELOG.md ---