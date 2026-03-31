CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」形式に準拠しています。  
バージョン/リリース日および主な変更点を日本語で記載しています。

雛形情報
-------
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py の __version__ に準拠）
- 初回リリース日: 2026-03-31

[Unreleased]
------------
（なし）

0.1.0 - 2026-03-31
-----------------
Added
- 基盤
  - パッケージの初期公開: kabusys（__all__ に data, strategy, execution, monitoring を公開）。
- 設定・環境変数管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準に探索）。
  - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーを実装:
    - export プレフィックス（export KEY=val）に対応。
    - シングル/ダブルクォートされた値のエスケープ処理対応。
    - クォート無し値でのインラインコメント判定（直前が空白/タブの場合に # をコメントとみなす）。
  - .env の読み込み挙動: OS 環境変数 > .env.local (上書き) > .env（未設定キーのみセット）。
  - 必須環境変数チェックを提供する Settings クラス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 標準的な設定値（DBパス、PIDファイル、閾値、KABUSYS_ENV, LOG_LEVEL）と値検証を実装。
- Data / ETL
  - ETL 用インターフェース公開 (kabusys.data.etl -> ETLResult の再エクスポート)。
  - ETL 実行結果を表す dataclass ETLResult を実装（品質問題・エラー収集、辞書変換ユーティリティ含む）。
  - pipeline モジュール: 差分更新、バックフィル、品質チェックを想定した設計の下でのユーティリティを実装（DuckDB 接続前提）。
  - calendar_management モジュール:
    - JPX マーケットカレンダー管理機能を実装（market_calendar テーブルを利用）。
    - 営業日判定、次/前営業日取得、範囲内営業日取得、SQ日判定のユーティリティを提供。
    - calendar_update_job による J-Quants からの差分取得・冪等保存の設計を追加（バックフィル、健全性チェック付き）。
    - カレンダーデータがない場合の曜日ベースフォールバック実装（DB データが不完全でも一貫した挙動）。
- Research（定量リサーチ）
  - research パッケージの公開関数群:
    - ファクター計算: calc_momentum, calc_value, calc_volatility
    - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
    - zscore_normalize を data.stats から再公開
  - factor_research:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算ロジックを実装（prices_daily を使用）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を実装。
    - Value: raw_financials を参照して PER, ROE を計算（最新の財務データを target_date 以前から取得）。
    - DuckDB SQL を用いた効率的なクエリ実装と不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証、単一クエリ取得）。
    - IC（Spearman の ρ）計算 calc_ic（ランク化、結合ロジック、最小サンプルチェック）。
    - ランキング関数 rank（同順位は平均ランク、丸めで ties 対策）。
    - factor_summary（count/mean/std/min/max/median の計算）。
- AI（OpenAI を利用した NLP）
  - kabusys.ai パッケージ初期実装:
    - news_nlp モジュール: ニュースを銘柄毎に集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ保存するワークフローを実装。
      - タイムウィンドウ（JST の前日15:00〜当日08:30相当）を calc_news_window で計算し、DB クエリは UTC naive datetime で実行。
      - 1 銘柄あたり最大記事数・文字数制限、バッチサイズ制御（最大20銘柄/コール）によるトークン肥大化対策。
      - JSON Mode を用いたレスポンス検証（レスポンス整形/抽出ロジック含む）。
      - リトライ（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフ実装。
      - レスポンスパース失敗や API エラー時は当該チャンクをスキップ、他チャンクは継続するフェイルセーフ設計。
      - DuckDB の executemany に対する空リスト回避処理（互換性確保）。
    - regime_detector モジュール: ETF 1321（225 連動ETF）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
      - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド回避）。
      - マクロ記事の取得フィルタ（マクロキーワード群）と OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価。
      - API 失敗時は macro_sentiment=0.0 とするフェイルセーフ、冪等な DB トランザクション（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - 共通設計:
    - OpenAI 呼び出し箇所は内部で _call_openai_api を定義し、テスト時にモック差し替えが可能。
    - 返却スコアは ±1.0 にクリップし、各所で安定化処理を実施。
    - モデル指定は gpt-4o-mini（コード上の定数で管理）。
- その他
  - DuckDB を前提とした SQL 実装と互換性注意（空 executemany 回避等）を考慮。
  - ロギング（logger）を各モジュールに導入し操作ログ・警告ログを充実。

Changed
- 初期リリースのため該当なし（新規実装）。

Fixed
- 初期実装段階の健全性対応を盛り込んだ（DB ロールバック、API エラーのフェイルセーフ、JSON パースの回復策等）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用する設計で、未設定時は ValueError を送出して誤った公開呼び出しを防止。
- .env 自動ロード時に OS 環境変数を保護する protected キーセットを用いて上書きを抑止。

注記 / 実装上の設計方針（重要点）
- ルックアヘッドバイアス回避: いずれの分析/スコア算出関数も内部で datetime.today() / date.today() を参照せず、引数の target_date に基づいて deterministically に計算する設計。
- テスト可能性: OpenAI 呼び出しや内部ユーティリティを差し替え可能（モック化）に実装。
- 冪等性: DB 書き込みは delete→insert 等で冪等化を意識。ETL 周りは差分更新・バックフィルを考慮。
- フォールバック挙動: API 失敗やデータ欠損時は安全側のデフォルト（例: スコア 0.0、MA 不足時は中立値 1.0）で継続し、例外を可能な限り上位に波及させない。

今後の予定（例）
- strategy / execution / monitoring パッケージの具体的実装（実運用向けの発注ロジックや監視機能の実装）。
- 単体テスト・統合テストの追加（OpenAI 呼び出しのモックを使った回帰テスト）。
- ドキュメント強化（API 仕様、データベーススキーマ、運用手順）。

---------------

（必要であればリリースノートを英語版に翻訳したり、日付・バージョンを調整できます。どの程度詳細に項目を分割するか指示をください。）