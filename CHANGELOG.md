# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
- （なし）

---

## [0.1.0] - 2026-03-29

Added
- 初回リリース: KabuSys パッケージを公開。
- パッケージメタ情報
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用途）。
    - .env と .env.local の読み込み優先順を実装（OS 環境変数は保護）。
  - .env パーサーは以下をサポート:
    - コメント行（#）、先頭の export キーワード、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理の差分対応。
  - Settings クラスでアプリケーション設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須キー検証（未設定時に ValueError を送出）。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証。
    - DB パスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI ニュース・レジーム関連（src/kabusys/ai/）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から指定ウィンドウ（JST: 前日15:00〜当日08:30）でニュースを集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズ、トークン肥大対策（最大記事数・最大文字数）を実装し、最大20 銘柄単位で処理。
    - JSON Mode を利用した厳密な JSON 出力期待、レスポンスの復元ロジック（前後の余計なテキストを含む場合に最外の {} を抽出）を実装。
    - リトライ戦略: 429 (RateLimit), ネットワーク断, タイムアウト, 5xx に対する指数バックオフ（最大リトライ回数制御）。
    - レスポンスバリデーション: results リスト構造、各要素の code/score 検証、未知コードの無視、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）。DuckDB executemany の空リスト制約を回避。
    - テスト容易性: _call_openai_api をモック差し替え可能。
  - マクロレジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily からの ma200_ratio 算出（ルックアヘッド防止のため target_date 未満のみ使用、データ不足時は中立扱い）。
    - raw_news をマクロキーワードでフィルタして LLM 評価を行い、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - OpenAI 呼び出しに対するリトライ（RateLimit/接続/タイムアウト/5xx）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行して例外伝播）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

- 研究（Research）モジュール（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から直近財務情報を取得して PER (EPS が無効な場合 None)、ROE を計算。
    - 設計: DuckDB 上で SQL ウィンドウ関数を活用して効率的に計算（外部 API にはアクセスしない）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。ホライズン検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満で None を返す。
    - rank: 同順位は平均ランクを返すランク関数（round(...,12) を用いた ties 対策）。
    - factor_summary: count/mean/std/min/max/median といった基本統計量を計算。
  - research パッケージは主要ユーティリティを再公開（zscore_normalize 等を含む）。

- データ基盤（src/kabusys/data/）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照した営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB に calendar データがない場合は曜日ベース（土日非営業）でフォールバック。DB 登録値が優先され、未登録日は曜日フォールバックで一貫した挙動。
    - 最長探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client）から差分でカレンダーを取得し market_calendar に冪等保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスの導入（ETL 実行結果の構造化: 取得数/保存数/品質問題/エラーなど）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）を想定した設計方針を実装（関数実装の一部とユーティリティを含む）。
    - DuckDB テーブル存在確認、最大日付取得ユーティリティを提供。
  - data.etl は ETLResult を再エクスポート。

- モジュール公開調整
  - ai.__init__ で score_news を公開（src/kabusys/ai/__init__.py）。
  - research.__init__ で主要関数群を再公開（src/kabusys/research/__init__.py）。

Security
- 環境変数の扱いに関する注意を README / .env.example 等へ記載推奨（Secrets: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN を必須で利用）。

Notes / Design decisions
- ルックアヘッドバイアス防止: 日付処理で datetime.today()/date.today() を結果計算に直接使わない設計（target_date ベースで動作）。
- フェイルセーフ設計: 外部 API 失敗時は例外で停止させずフェイルオーバー（スコア 0.0、スキップ等）して処理継続する部分が多い。
- テスト支援: OpenAI 呼び出しをラップした内部関数をモック可能にして単体テストを容易化。
- DuckDB の互換性配慮: executemany の空リスト制約など実運用での注意点に対応。

Fixed
- （初回リリースのためなし）

Changed / Deprecated / Removed
- （初回リリースのためなし）

Security
- （初回リリースのためなし）

---

開発者向けメモ
- 必須環境変数:
  - OPENAI_API_KEY (AI モジュール)
  - JQUANTS_REFRESH_TOKEN (データ ETL)
  - KABU_API_PASSWORD, KABU_API_BASE_URL (kabu ステーション API)
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知)
- テスト時の環境制御:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化して環境を明示的に組み立てられる。

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートには運用上の注意や既知の制約、マイグレーション手順などを併記してください。）