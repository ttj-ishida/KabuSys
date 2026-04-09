CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

未リリース
---------

（なし）

0.1.0 - 2026-04-09
------------------

Added
- 初期リリースとして以下の主要モジュールを追加（パッケージバージョン: 0.1.0）。
  - パッケージ情報
    - src/kabusys/__init__.py
      - __version__ = "0.1.0"
      - __all__ に主要サブパッケージをエクスポート

  - 環境変数・設定管理
    - src/kabusys/config.py
      - .env ファイルまたは既存の OS 環境変数から設定値を読み込む自動ローダを実装
        - 自動読み込み順序: OS 環境変数 > .env.local > .env
        - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能
        - プロジェクトルートは __file__ を基点に .git または pyproject.toml で探索（配布後も動作）
        - .env パーサーは export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いの細やかな処理を実装
        - .env 読み込み時、既存の OS 環境変数は protected として上書き防止（.env.local は override=True による上書きが可能だが protected を尊重）
      - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu / LINE / DB /監視 / システム等）
        - 必須値取得時の _require() による明示的な ValueError
        - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値検証（不正値時は ValueError）
        - デフォルト値（例: KABUS_API_BASE_URL, DB パス, 監視閾値など）を定義

  - ポートフォリオ構築（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: score 降順、同点は signal_rank の昇順でタイブレーク
      - calc_equal_weights: 等金額配分
      - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバックし WARNING ログ出力
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存保有の時価ベースを計算し、上限超過セクターの新規候補を除外）
        - "unknown" セクターは上限適用対象外
        - 当日売却予定銘柄をエクスポージャー計算から除外可能
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップ、未知値は警告して 1.0 にフォールバック）
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes:
        - allocation_method: "risk_based" / "equal" / "score" をサポート
        - risk_based: 許容リスク率(risk_pct)、損切り率(stop_loss_pct) を用いた株数算出
        - equal/score: weight に基づく割付け、portfolio_value・max_utilization を考慮
        - lot_size（単元）に基づく丸め処理、max_position_pct による per-stock 上限
        - aggregate cap: 全銘柄合計が available_cash を超える場合はスケールダウンし、端数は lot 単位で残差の大きい順に再配分
        - cost_buffer による手数料/スリッページの保守的見積り反映
    - src/kabusys/portfolio/__init__.py で主要関数を公開

  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を DuckDB の SQL ウィンドウ関数で計算。データ不足時は None を返す仕様
      - calc_volatility: 20 日 ATR（true range の NULL 伝播を適切に制御）、相対 ATR、20 日平均売買代金、出来高比率を計算
      - calc_value: raw_financials から最新財務データを取得し PER/ROE を価格と結合して算出（EPS が 0/欠損のときは None）
      - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照（外部 API へアクセスしない）
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算、horizons の検証（1..252）
      - calc_ic: スピアマンランク相関（ランクの ties は平均ランク処理）。有効レコード < 3 の場合は None
      - rank: 小数丸め (round(v,12)) による ties 安全化と平均ランク化
      - factor_summary: count/mean/std/min/max/median を計算（None を除外）
    - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize を含む）

  - AI（LLM）関連
    - src/kabusys/ai/news_nlp.py
      - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込むワークフローを実装
        - ニュース時間ウィンドウ計算（JST ベース → DB は UTC 前提）
        - 銘柄ごとに記事を集約し、最大記事数/文字数でトリム
        - 最大 _BATCH_SIZE=20 銘柄でバッチ送信、JSON mode を使用して厳密な JSON を期待
        - 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）
        - レスポンスの堅牢なバリデーション（JSON 抽出、results 列存在確認、コード整合性、スコア数値変換、±1.0 でクリップ）
        - DuckDB への書き込みは部分更新（DELETE 個別実行 → INSERT executemany）で冪等性と部分失敗時保護を実現
      - API キー必須（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError
      - テスト用に _call_openai_api の差し替えが容易な設計
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジームを判定
        - ma200 の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）
        - マクロニュースはキーワードフィルタでタイトルを抽出、記事が無い場合は LLM 呼び出しを行わず macro_sentiment=0.0 とする
        - レジームスコア合成後、閾値により 'bull'/'neutral'/'bear' を決定
        - DB への冪等書き込みを実装（BEGIN / DELETE / INSERT / COMMIT）
      - API キー必須（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError
      - news_nlp の calc_news_window を再利用しつつ、内部の OpenAI 呼び出しはモジュール間で共有しない実装

  - 監視ログ永続化
    - src/kabusys/monitoring/monitoring_db.py
      - init_monitoring_db: SQLite 接続に対して system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等に作成する初期化機能を追加

Security
- OpenAI API キーは必須機密情報。score_news / score_regime の呼び出しには api_key 引数か環境変数 OPENAI_API_KEY のいずれかを設定する必要があります。

Notes / 注意点
- ルックアヘッドバイアス防止:
  - news_nlp / regime_detector などの日次判定ロジックは date パラメータを明示的に受け取り、date.today()/datetime.today() を参照しない設計です。
  - prices_daily クエリでも target_date 未満のデータのみを使用するよう配慮しています。
- DuckDB / SQLite の executemany に関する互換性注意:
  - DuckDB 0.10 系では executemany に空リストを渡せないため、書き込み前に空チェックを行っています。
- 自動 .env ロードはプロジェクトルートの検出に成功しない場合はスキップされます（配布後の環境で安全に動作）。

今後の予定（提案）
- portfolio.position_sizing の lot_size を銘柄別に対応する拡張（stocks マスタから lot_size を取得）
- .env パーサーのより詳細なエスケープ/エンコーディング検証、または既存ライブラリ採用の検討
- research モジュールの追加ファクター（PBR、配当利回り等）実装
- テストカバレッジ強化（特に LLM API 呼び出し周りのモックとエラーシナリオ）

----