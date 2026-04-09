Changelog
=========

すべての重要な変更はこのファイルに記録します。  
このフォーマットは Keep a Changelog に準拠します。  
リリース日はコードベースから推測した作成日を使用しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初回リリース（kabusys v0.1.0）
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__="0.1.0" を設定。
    - 公開モジュールとして data, strategy, execution, monitoring を __all__ に定義。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
      - 読み込み順序: OS 環境変数 > .env.local > .env
      - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装:
      - export KEY=val 形式の対応、シングル/ダブルクォートのエスケープ処理、インラインコメント考慮。
    - Settings クラスでアプリ設定を提供:
      - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等の必須設定取得（未設定時は ValueError）。
      - 各種デフォルト値を提供（例: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など）。
      - 環境値検証（KABUSYS_ENV の有効値、LOG_LEVEL の有効値、PAPER_FILL_MODE の有効値チェック）。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選別（タイブレーク: signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等分にフォールバックし WARNING ログを出力）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 複数方式の株数算出を実装（risk_based / equal / score）。
      - リスクベースの算出（risk_pct, stop_loss_pct を考慮）。
      - lot_size（単元株）丸め、per-position および aggregate 上限、コストバッファ（手数料・スリッページ）対応。
      - 可用現金に応じたスケーリング（端数配分は残差に基づき lot 単位で追加配分、再現性確保）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクター比率上限をチェックし、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知レジーム時はフォールバックで 1.0、警告ログ）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を計算。データ不足時は None を返す挙動。
    - calc_volatility: 20日 ATR、ATR/株価、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を明示的に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損の場合は None）、ROE を計算。target_date 以前の最新財務データを取得する仕組み。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。ペアが 3 件未満の場合は None。
    - rank: 同順位は平均ランクとなるランク付け（丸めにより ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出（None を除外）。
  - src/kabusys/research/__init__.py で各関数を公開（zscore_normalize を data.stats から再エクスポート）。

- AI（LLM）連携機能
  - src/kabusys/ai/news_nlp.py
    - raw_news をバッチで LLM（OpenAI: gpt-4o-mini）に投げて銘柄別センチメント（ai_score）を計算し ai_scores テーブルへ書き込む。
    - 主な特徴:
      - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する util（calc_news_window）。
      - 1銘柄当たりの最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ _BATCH_SIZE（20 銘柄）でバッチ送信、JSON Mode を利用。
      - 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。その他エラーはスキップ（フェイルセーフ）。
      - レスポンス検証とスコアの ±1.0 クリップ、部分書き換え（DELETE→INSERT の組み合わせ）で冪等性と部分失敗耐性を確保。
      - OpenAI API 呼び出しポイントを抽象化（テスト時は差し替え可能）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム判定（bull/neutral/bear）を行い market_regime テーブルへ書き込み。
    - マクロニュースはキーワードフィルタで抽出（複数キーワード）。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 とするフェイルセーフ挙動。
    - OpenAI 呼び出しのリトライとエラーハンドリングを実装。内部で calc_news_window を再利用。
  - src/kabusys/ai/__init__.py で score_news を公開。

- 監視ログ永続化層（SQLite）
  - src/kabusys/monitoring/monitoring_db.py
    - init_monitoring_db: system_status, trade_logs, positions, risk_logs などのテーブルとインデックスを冪等的に作成するスクリプトを提供。
    - SQLite を使ったシンプルな監視・ログ保存レイヤ。ビジネスロジックは持たず読み書き用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / その他
- 環境変数や外部 API キー (OPENAI_API_KEY) が未設定の場合は明確な ValueError を投げて早期に検出できる設計。
- 全体的に「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計方針を採用。
- OpenAI との連携部分は API エラー時に安全にフォールバックする（部分失敗の保護、警告ログ出力）。
- DuckDB / SQLite のクエリは互換性や DuckDB の executemany の制約に配慮して実装されている（空パラメータの扱い等）。

Acknowledgements
- 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。リリース日や細かな文言はソースコードの最終更新日やリポジトリ運用方針に合わせて調整してください。