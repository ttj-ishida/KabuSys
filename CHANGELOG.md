# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従います。  

なお、以下は提供されたコードベースから推測して作成した変更履歴です。実際のコミット履歴ではありません。

## [Unreleased]

### 追加予定 / 今後の改善案
- 個別銘柄ごとの lot_size を stocks マスタから読み込むなど、calc_position_sizes の lot_size を銘柄別に対応する拡張（現状 TODO 注記あり）。
- .env ローダーのフォールバック価格（price が 0.0 の場合の扱い）改善（risk_adjustment.apply_sector_cap 内の TODO）。前日終値や取得原価などの利用検討。
- DuckDB / SQLite のバージョン互換性に関する追加検証とエラーハンドリングの強化。
- 単体テスト・統合テストの追加（OpenAI API 呼び出しはモック可能な設計になっているが、テストケースを整備予定）。

---

## [0.1.0] - 2026-04-09

### 追加
- パッケージ基礎
  - 初期バージョン 0.1.0 を追加。パッケージ名 kabusys を定義。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数は protected として上書きを制御。
  - .env 行パーサ実装:
    - コメント、`export KEY=val` 形式、シングル/ダブル引用符、エスケープ、インラインコメントの扱いをサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能。
    - J-Quants / kabuステーション / LINE API / DB パス（DuckDB/SQLite）など主要設定を網羅。
    - 各種バリデーション実装（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL の制約）。
    - ファイルパスは Path.expanduser() を用いて解決。

- ポートフォリオ構築 (src/kabusys/portfolio)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）で上位 N 件選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime ('bull'/'neutral'/'bear') に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0、警告ログ）。
  - position_sizing.py
    - calc_position_sizes: allocation_method に基づき発注株数を計算（"risk_based", "equal", "score" 対応）。
      - risk_based: 許容リスク率 / 損切り率からポジションサイズ算出。
      - equal/score: 重みと価格から計算、per-position と portfolio レベルでキャップを適用。
      - lot_size（単元株）考慮、cost_buffer による保守的なコスト見積り。
      - aggregate cap により可用現金を超過する場合はスケールダウンし、端数は lot_size 単位で残差配分（再現性確保のソート順あり）。
      - 価格欠損（None / <=0）の銘柄はスキップしログ出力。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB の prices_daily を用いて計算。データ不足時は None を返却する挙動を明示。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から最新の財務指標（eps, roe）を取得し PER・ROE を算出。その他指標（PBR・配当利回り）は未実装として注記。
  - feature_exploration.py
    - calc_forward_returns: target_date から各ホライズン先の将来リターンを一括 SQL で取得（ホライズン検証あり）。
    - calc_ic / rank: スピアマンのランク相関（IC）計算、同順位は平均ランクを割り当てる rank 実装。
    - factor_summary: count/mean/std/min/max/median といった統計サマリーを標準ライブラリのみで計算。
  - research パッケージ初期エクスポートに zscore_normalize を含む（kabusys.data.stats 依存）。

- AI 関連 (src/kabusys/ai)
  - news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）へ送りセンチメント（ai_score）を生成し ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ計算（JST基準の前日15:00〜当日08:30 に対応、UTC 変換実装）。
    - 記事の集約・トリム（記事数上限・文字数上限）、最大 20 銘柄バッチ、JSON Mode での応答検証。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ、その他はスキップ）。
    - 応答パースの堅牢化（JSON decode 失敗時に外側の {} を抽出して復元を試みる等）、スコアを ±1.0 にクリップ。
    - データベース書き込みは冪等的に DELETE → INSERT（部分失敗時に他銘柄スコアを保護）。
    - OpenAI 呼び出しは _call_openai_api を介しており、ユニットテストで差し替え可能。
  - regime_detector.py
    - ETF 1321 の 200 日 MA 乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付けして市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - マクロニュース抽出はキーワード一致（複数キーワードリスト）でタイトルを取得、最大件数制限あり。
    - LLM 呼び出しはリトライ戦略を備え、失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 合成スコアの閾値でラベル付けし market_regime テーブルへ冪等書き込みを行う。
    - news_nlp.calc_news_window を共通に利用。

- モニタリング DB (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を利用した監視ログ永続化層を追加（ビジネスロジックを持たず読み書きのみ）。
  - init_monitoring_db 関数で冪等に以下のテーブル・インデックスを作成:
    - system_status（CPU/メモリ/ディスク/プロセス状態 等）およびそのインデックス
    - trade_logs（イベントログ、client_order_id インデックス 等）
    - positions（code を主キー、更新日時インデックス 等）
    - risk_logs（構造化されたリスクログ。スクリプトにより作成）
  - （注）スキーマ定義には複数テーブルとインデックスが含まれる。詳細はモジュール内の SQL を参照。

### 変更
- パッケージ構成を整理し、各モジュールを __all__ で公開（portfolio, research, ai など）。

### 修正 / 安定化
- 入力検証・フォールバックを多めに実装しており、外部 API 失敗時やデータ欠損時に例外を投げずに安全なデフォルトで継続する設計（AI モジュール・レジーム判定・ファクター計算の多くで採用）。
- DuckDB・SQLite の executemany に関する互換性考慮（空リストバインド回避）を実装。

### 既知の制限（Documentation / TODO として明示）
- price が欠損（0.0）だと sector_exposure が過少評価されセクターキャップが外れる可能性がある点（apply_sector_cap 内に TODO）。
- PBR 等一部バリュー指標は未実装（calc_value の注記）。
- 現在 lot_size は全銘柄共通の引数で渡す設計。将来的に銘柄別対応を検討。
- OpenAI API に依存する処理はネットワークや API 仕様に影響されうるため、実運用では API キー管理・レート制限対応・コスト管理が必要。

---

履歴の追加・修正・詳細化を希望する場合は、反映したい差分（実際のコミットメッセージやファイル変更点）を提供してください。