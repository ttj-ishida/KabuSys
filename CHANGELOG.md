Keep a Changelog形式に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコード内容から推測して記載しています。

保持方針:
- これは初期リリース（v0.1.0）相当の変更履歴です。
- 各モジュールごとに「追加（Added）」「変更（Changed）」「修正（Fixed）」の観点で要点を列挙しています。
- 実装上の重要な設計決定やフェイルセーフの挙動も記載しています。

CHANGELOG.md
==================================================

全般
-----
- フォーマット: Keep a Changelog 準拠
- バージョン: 0.1.0
- リリース日: 2026-03-31
- 概要: 日本株自動売買システム「KabuSys」初期リリース相当の実装。データ取得・ETL・市場/ニュースのAI評価・ファクター計算・カレンダー管理・設定管理などを包含。

v0.1.0 - 2026-03-31
-------------------

Added
- 基本パッケージ
  - パッケージ名とバージョンを導入: kabusys v0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API に data, strategy, execution, monitoring を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出 ( .git または pyproject.toml を基準 ) により CWD に依存しないロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサー実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - インラインコメントの扱い（クォートなしでは直前の空白／タブでコメント判定）。
  - .env 読み込みの override/protected メカニズム:
    - override=True で既存値を上書き（ただし protected（OS 環境変数）を保護）。
  - Settings クラスを導入:
    - J-Quants / kabu ステーション / Slack / DB パス / 監視しきい値 / システム設定などのプロパティを提供。
    - 必須環境変数未設定時は分かりやすい ValueError を送出。
    - KABUSYS_ENV の検証、LOG_LEVEL の検証、利便性プロパティ（is_live, is_paper, is_dev）を提供。

- AI モジュール (src/kabusys/ai)
  - ニュースNLPスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、OpenAI(gpt-4o-mini) を用いて銘柄ごとにセンチメント（-1.0〜1.0）を評価。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC換算済み）。
    - チャンク処理・バッチ送信（最大 20 銘柄/回）、1銘柄あたり記事数上限・文字数上限でトリム。
    - JSON Mode を想定したレスポンス検証と堅牢なパース（余分なテキストを含むケースの復元処理含む）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。その他のエラーはフェイルセーフでスキップ。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、書き込みは対象 code のみ DELETE→INSERT。
    - ユニットテスト容易化のため OpenAI 呼び出し関数をパッチ可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウを算出、raw_news からマクロキーワードで抽出。
    - OpenAI によるセンチメント取得は冗長ハンドリング（リトライ・500系特別処理）を含む。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームスコアの計算・閾値・ラベル付けを実施し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - 公開 API: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間差分更新処理（calendar_update_job）と営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB に calendar 情報が無い場合は曜日ベースのフォールバック（週末 = 非営業日）で一貫した動作を保証。
    - 更新は J-Quants から差分フェッチして idempotent に保存。バックフィルや健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を公開（ETL 実行結果の構造体: 取得数・保存数・品質問題・エラー一覧を保持）。
    - 差分取得、保存（idempotent）、品質チェックの設計方針を実装。
    - jquants_client と quality モジュールに依存する ETL ワークフローの基盤を用意。
  - 互換性: data.__init__ などで pipeline の ETLResult を再エクスポート。

- リサーチ（ファクター研究） (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/3m/6m, ma200_dev（MA200乖離）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から最新の EPS/ROE を用いて PER/ROE を計算。EPS が 0/欠損時は None。
    - 実装は DuckDB + SQL ウィンドウ関数で効率的に実施。外部 API へはアクセスしない。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズンの将来リターン（horizons デフォルト [1,5,21]）を計算。horizons の検証を実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research.__init__ で主要関数をエクスポート（zscore_normalize は data.stats から取り込み）。

Changed
- 設計方針の明示化（各モジュール）
  - ルックアヘッドバイアス防止のため日付取得（datetime.today()/date.today()）を関数内部で直接参照しない実装方針を採用。全関数が target_date を明示的に受け取る。
  - OpenAI API 呼び出し箇所に対して、ユニットテストで差し替え可能な _call_openai_api 層を設置し結合度を低減。
  - DuckDB による書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で安全に実施。部分書き込みや部分失敗時に既存データを保護するため、対象コードを限定して DELETE→INSERT を行う設計とした。
  - executemany に対して空リストを渡さないチェックを追加（DuckDB 互換性対応）。

Fixed
- フェイルセーフ / エラー処理の強化
  - OpenAI API 呼び出しでの各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）を個別に扱い、リトライ戦略や非 5xx エラー時のスキップを実装。
  - JSON レスポンスパース失敗時のログ出力とフォールバック（スコア 0.0 の採用やスキップ）による堅牢性向上。
  - market_regime / ai_scores への DB 書き込み失敗時に ROLLBACK を試み、ROLLBACK 失敗は警告ログで通知。

Notes / Implementation details
- OpenAI モデル: gpt-4o-mini を想定し JSON mode を利用する設計。レスポンスは厳密な JSON を期待するが、余分なテキスト混入に備えた復元ロジックを実装。
- マクロキーワード・ウィンドウサイズ・各種しきい値（MA ウィンドウ、ATR 期間、バッチサイズ等）はモジュール内定数として管理。
- テストしやすさを重視して、外部 API 呼び出しや時刻決定ロジックを注入可能（パッチして差し替え）にしている。
- J-Quants / kabu ステーション / Slack 等の接続情報は Settings クラスを通じて環境変数から取得する設計。

Future / TODO（推測）
- strategy / execution / monitoring の具体実装（パッケージ __all__ に含まれるが該当ファイルは今回のスニペットに含まれず）。
- テストカバレッジの整備（OpenAI 呼び出しモック、DuckDB のインメモリテストなど）。
- エンドツーエンドの ETL 実行・バックフィルジョブの運用監視設定追加。

==================================================

必要に応じて、さらに詳細なセクション（例: モジュール別 API 使用例、環境変数一覧、契約済み外部サービス別注意点など）を追加できます。どの範囲まで詳細化しますか？