# Changelog

すべての重要な変更点を記録します。本書式は「Keep a Changelog」に準拠します。  
バージョニングはセマンティックバージョニングに従います。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な機能と設計方針は以下の通りです。

### Added
- パッケージ公開
  - kabusys パッケージ本体を追加。バージョンは `0.1.0`。
  - 主なサブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に登録）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数を統合して読み込む設定管理を実装。
  - プロジェクトルート検出: __file__ を起点に `.git` または `pyproject.toml` を探索して自動的にプロジェクトルートを特定。
  - .env 読み込みロジック:
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能
    - エクスポート形式（`export KEY=val`）やクォート/エスケープ、インラインコメントの取り扱いに対応する堅牢なパーサを実装
    - ファイル読み込み失敗時は警告を出力して安全に継続
  - Settings クラスを提供し、必要な設定をプロパティで取得:
    - J-Quants / kabu API / Slack / DB パスなど（必須項目は未設定時に ValueError を送出）
    - KABUSYS_ENV の値検証（development/paper_trading/live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live/is_paper/is_dev の判定プロパティ

- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
    - 処理のポイント:
      - JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換）
      - 1銘柄あたり最大記事数・文字数の制限（トークン肥大対策）
      - 最大 BATCH_SIZE（20銘柄）でのバッチ送信
      - レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ
      - レスポンスバリデーション（JSON 抽出・results フォーマットチェック・スコア数値化・±1.0 クリップ）
      - 部分失敗時に既存スコアを保護するため、取得成功銘柄のみ DELETE→INSERT による置換
      - テスト容易性: OpenAI 呼び出し部分は内部関数を patch して差し替え可能
  - kabusys.ai.regime_detector
    - 日次の市場レジーム（bull/neutral/bear）判定機能を実装（score_regime）。
    - 処理のポイント:
      - ETF 1321 の 200 日移動平均乖離（ma200_ratio）を主要入力（重み 70%）
      - news_nlp のマクロキーワードでフィルタしたニュースを LLM（gpt-4o-mini）でセンチメント評価（重み 30%）
      - レジームスコア合成（クリップ）によりラベル判定（閾値で bull/bear 判定）
      - OpenAI API 呼び出しのリトライとフェイルセーフ（API 失敗時は macro_sentiment = 0.0）
      - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理の適切なハンドリング
      - テスト容易性: API キー注入と内部 API 呼び出し差替え可能

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX マーケットカレンダーの読み書き・営業日判定ユーティリティを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB に登録がない日については曜日ベース（土日非営業日）でフォールバック
    - 最大探索日数制限や健全性チェックを導入して無限ループや誤った将来日付を防止
    - calendar_update_job: J-Quants API から差分を取得し market_calendar を冪等に更新（バックフィル期間を確保）
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（ETL 実行結果の標準形）
    - ETL の設計方針（差分更新、バックフィル、品質チェックの集約、id_token 注入によるテスト性向上）を実装
    - テーブル最大日付取得や存在チェックなどのユーティリティ実装

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を計算
    - 全て DuckDB 上の SQL と標準ライブラリで完結（外部 API 不使用）
    - データ不足時の扱い（十分な履歴がない場合は None を返す）
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンをまとめて算出
    - calc_ic: スピアマン順位相関（IC）計算（None と重複処理の扱い）
    - rank: 同順位は平均ランクとするランク付け
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - データ正規化ユーティリティ（zscore_normalize）は data.stats から再エクスポート

### Changed
- （初期リリースのため過去からの変更はありません）

### Fixed
- トランザクション処理におけるロールバック安全化:
  - DB 書き込み失敗時に ROLLBACK を試み、さらに ROLLBACK 自体の失敗も警告としてロギングすることで復旧性を向上。
- OpenAI API 呼び出し関連:
  - 5xx / タイムアウト / 接続エラーはリトライ対象として扱い、非 5xx エラーは即座にフェイルセーフで継続する実装。

### Security
- 環境設定の取り扱い:
  - OS 環境変数は保護（protected set）され、.env/.env.local による上書きから守る仕組みを導入。

---

注記:
- 多くの関数・処理で「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計となっています。全ての関数は引数として target_date を受け取り、過去データのみを参照することを保証しています。
- OpenAI 呼び出し箇所はテスト容易性を考慮して差し替え可能に実装されています（unittest.mock.patch 等でモック可能）。
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は変更差分やコミットログを参照して追記・修正してください。