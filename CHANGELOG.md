CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし（初回リリースは 0.1.0 を参照）

[0.1.0] - 2026-04-09
-------------------

Added
- 初期リリース。以下の主要機能を実装。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0" を設定。
    - パッケージ公開用 __all__ に主要サブモジュールを定義。
  - 環境設定管理 (kabusys.config)
    - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント対応。
    - OS 環境変数を保護する protected 機構を実装（.env の上書きを制御）。
    - Settings クラスを提供し、J-Quants・kabu API・LINE・DB パス・監視閾値・環境・ログレベル等の設定プロパティを公開。
    - 設定値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を実装。
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder:
      - select_candidates: BUY シグナルのスコア順ソートと上位選出。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（既存保有の時価ベースでブロック）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）。
    - position_sizing:
      - calc_position_sizes: risk_based / equal / score の各方式に対応した発注株数計算。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、手数料スリッページ用 cost_buffer を考慮した保守的見積りを実装。
      - raw_shares をスケールダウンする際の再配分（fractional remainder を基に lot 単位で追加）を実装。
  - リサーチ（ファクター計算・特徴量解析） (kabusys.research)
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB の prices_daily を参照）。
      - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の計算。
      - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算。
      - DuckDB を使った SQL 実装で、ルックアヘッド対策や欠損データの取扱いを考慮。
    - feature_exploration:
      - calc_forward_returns: 複数ホライズンの将来リターンを一括で取得（horizons のバリデーションあり）。
      - calc_ic: スピアマンランク相関（IC）の計算（None 値・不足レコードを除外、3 件未満で None を返す）。
      - factor_summary / rank: 基本統計量算出、同順位の平均ランクを扱うランク関数を実装。
    - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats のユーティリティ）を含む。
  - AI モジュール (kabusys.ai)
    - news_nlp:
      - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し銘柄毎にセンチメント ai_score を計算、ai_scores テーブルへ書込。
      - タイムウィンドウ計算（JST ベース -> UTC 変換）を提供（calc_news_window）。
      - トークン肥大化対策（1 銘柄あたりの記事数/文字数の上限）、バッチサイズ制御、JSON モードのバリデーション、スコアクリッピング（±1.0）。
      - API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx をリトライ（指数バックオフ）、その他エラーはフェイルセーフでスキップ。
      - レスポンスの堅牢なパース（JSON mode でも余計な前後テキストが混入するケースを復元して抽出）。
      - DuckDB への書き込みは部分失敗に備え、対象 code のみを DELETE → INSERT で置換（executemany の空リスト制約を考慮）。
    - regime_detector:
      - ETF 1321 の MA200 乖離とマクロニュース LLM センチメントを合成して market_regime を判定・保存。
      - マクロニュースはキーワードフィルタで抽出し（日本 & 米国を想定したキーワードリスト）、LLM で macro_sentiment を評価。
      - ma200_ratio 計算は target_date 未満のデータのみ使用（ルックアヘッド対策）、データ不足時は neutral 相当のフォールバック。
      - LLM 呼出は retry/backoff を実装し、失敗時は macro_sentiment=0.0 としてフォールバック。
      - 判定結果は冪等に market_regime テーブルへ書き込む（BEGIN / DELETE / INSERT / COMMIT）。
  - 監視ログ永続化 (kabusys.monitoring)
    - monitoring_db.init_monitoring_db: SQLite 用の監視関連テーブルとインデックスの作成スクリプト（冪等）を提供。
      - system_status, trade_logs, positions, risk_logs などのスキーマを初期実装（スキーマの一部が出力に含まれる形で実装）。

Changed
- このリリースは初版のため変更履歴なし。

Fixed
- このリリースは初版のためバグ修正履歴なし。

Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用。未設定時は明示的に ValueError を送出して誤った静的フォールバックを防止。

Notes / Design decisions
- ルックアヘッドバイアス防止のため、日付計算や DB クエリは target_date の扱いに注意して実装（datetime.today()/date.today() を直接参照しない）。
- DuckDB / SQLite を直接操作する関数は外部 API を呼ばずに純粋なデータ処理に留める設計（本番発注 API にはアクセスしない）。
- .env パーサは現実的な表記（export、クォート、エスケープ、インラインコメント）に対応しているが、特殊ケースが残る可能性あり。
- 堅牢性重視のため、AI 系処理は API パースや通信失敗に対して「安全なフォールバック」を採用（例: macro_sentiment=0.0、空レスポンス時は該当銘柄のスコア未更新）。

Known issues / TODO
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、セクターエクスポージャが過少見積になりブロックが外れる可能性がある。将来的に前日終値や取得原価などのフォールバックを検討。
- position_sizing:
  - lot_size は現在グローバル固定で 100 を想定。将来的に銘柄別 lot_map を受け取る設計に拡張予定。
- news_nlp / regime_detector:
  - LLM とやり取りする内部の API 呼び出し関数はテスト時に差し替え可能だが、統合テストでは本物の API と接続しないモックが必要。
- monitoring_db のスキーマは今後の拡張で変更される可能性がある（マイグレーション戦略の検討が必要）。

Breaking Changes
- なし（初回リリース）。

Acknowledgements
- 本 CHANGELOG は提供されたコードベースの実装内容から推測して作成しています。実際のリリースノートはリリース時のコミット・PR を基に追記・修正してください。