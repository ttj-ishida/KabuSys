# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用しています。
このファイルはコードベースから推測できる機能と設計上の決定を基に作成しています。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 初期リリース
公開日: 2026-03-31

注: 本バージョンはリポジトリの現状（src/kabusys 以下のモジュール）を初期リリースとしてまとめたものです。

### 追加（Added）
- パッケージ基礎
  - kabusys パッケージを追加。パッケージバージョンは `0.1.0`。
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を用意。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数を自動で読み込む仕組みを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパース実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、主要設定をプロパティとして取得可能:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite） / 実行環境（development/paper_trading/live）/ログレベル
    - 必須設定未提供時は分かりやすいエラーメッセージを送出。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェック方針を実装。
    - ETL 実行結果を表す dataclass `ETLResult` を公開（kabusys.data.etl で再エクスポート）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - 夜間バッチ更新ジョブ `calendar_update_job`（J-Quants から差分取得して market_calendar を冪等に保存）。
    - DB 未取得時の曜日ベースフォールバック、検索上限・健全性チェック・バックフィルの実装。

- 研究（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を追加:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - データ不足時の挙動（None を返す）や計算ウィンドウの設計が明文化されている。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)
      - デフォルト horizons = [1,5,21]
    - IC 計算（Spearman 的ランク相関）: calc_ic(...)
    - ランク変換ユーティリティ: rank(values)
    - ファクター統計サマリ: factor_summary(records, columns)

- AI（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコアを算出する処理を追加。
    - 処理特徴:
      - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
      - バッチサイズ、最大記事数・文字数トリム、最大リトライ（429/ネットワーク/5xx）などを実装。
      - レスポンスのバリデーション・スコアのクリップ（±1.0）・部分成功時の DB 書き込み保護（対象コードのみ DELETE → INSERT）。
    - パブリック API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - 処理特徴:
      - DuckDB の prices_daily/raw_news を参照しルックアヘッドを防止する設計。
      - OpenAI API 呼び出しに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
      - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - パブリック API: score_regime(conn, target_date, api_key=None)

- OpenAI 統合
  - OpenAI クライアント（gpt-4o-mini）を用いた JSON Mode での呼び出しを採用。
  - 各モジュールで API 呼び出しをラップした内部関数を用意しており、テスト時に差し替え可能（unittest.mock.patch を想定）。

- DuckDB を主要なローカル DB エンジンとして利用
  - 多数のクエリと window 関数を活用した実装。DuckDB の executemany の制約等に配慮したコード（空リスト guard 等）。

### 変更（Changed）
- 初期リリースのため該当なし。

### 修正（Fixed）
- 初期リリースのため該当なし。

### 削除（Removed）
- 初期リリースのため該当なし。

### セキュリティ（Security）
- 初期リリースのため該当なし。
- 注意事項:
  - OpenAI API キーや各種トークンは環境変数で管理（Settings で必須チェック）。
  - .env 読込の上書きルールに OS 環境変数保護（protected set）を導入。

### 開発者向け備考 / 設計上の重要ポイント
- ルックアヘッドバイアス対策: date.today()/datetime.today() の直接参照を避け、target_date 引数ベースで全ての時系列処理を行う設計。
- フェイルセーフ: 外部 API の失敗時は原則スキップやデフォルト値（例: macro_sentiment=0.0）で継続し、重大エラーは上位に伝播させる。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト容易性: OpenAI 呼び出し関数を内部で分離しているため、ユニットテストでモック差し替えが可能。
- パフォーマンスと互換性: DuckDB のバージョン差異（list バインドの不安定さ等）を考慮した実装がされている。

---

著: 自動生成（コードベースから推測）  
注: 実際のリリース日や文言はプロジェクトの方針に合わせて調整してください。