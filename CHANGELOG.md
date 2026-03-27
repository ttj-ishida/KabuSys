# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
安定版リリースはセマンティックバージョニングに従います。

なお本 CHANGELOG は与えられたコードベースの内容から実装状況・設計意図を推測して作成したものであり、実際のコミット履歴やリリースノートとは異なる場合があります。

# Unreleased
- （なし）

## [0.1.0] - 2026-03-27
最初の公開リリース。日本株自動売買プラットフォームのコア機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを導入。公開バージョンは `0.1.0`。
  - パッケージ公開インターフェースを `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env パーサーを実装：コメント行・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントの取り扱いに対応。
  - .env の読み込み順序を OS 環境 > .env.local > .env とし、OS 環境変数保護用に protected セットを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを提供し、必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL、データベースパス等）、環境（development/paper_trading/live）とログレベルのバリデーションを実装。

- データ取り扱い（kabusys.data）
  - ETL 用の公開インターフェース `ETLResult` を実装（kabusys.data.pipeline から再エクスポート）。
  - DuckDB を前提とした ETL パイプライン基盤（差分取得・保存・品質チェック・バックフィル）を実装。ETL の実行結果を表すデータクラス `ETLResult` を提供。
  - 市場カレンダー管理（kabusys.data.calendar_management）を実装。機能：
    - 営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ日判定（is_sq_day）。
    - J-Quants からの差分取得を行う夜間バッチジョブ `calendar_update_job`、バックフィルや健全性チェックを含む。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）を採用。
    - DuckDB の date 型・NULL 値・テーブル存在チェックの扱いを明示。

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）を実装：
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: raw_financials から EPS/ROE を参照して PER/ROE を算出。EPS が 0 または欠損の場合は PER を None にする。
    - 各関数は DuckDB 接続を受け取り SQL で計算し、(date, code) をキーとする dict のリストで結果を返す。
  - 特徴量探索（kabusys.research.feature_exploration）を実装：
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）で LEAD を用いて将来終値からリターンを計算。horizons のバリデーション有り。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関をランク関数を用いて算出。3件未満で計算不可。
    - ランク変換（rank）：同順位は平均ランクを返す実装（丸め処理で ties の検出を安定化）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。

- AI / ニュース解析（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）を実装：
    - ニュースの収集ウィンドウ（JST 前日15:00 ～ 当日08:30 相当）を UTC naive datetime で計算する `calc_news_window`。
    - raw_news と news_symbols を結合して銘柄毎に記事を集約し、銘柄ごとに最大記事数・最大文字数でトリムして OpenAI（gpt-4o-mini）にバッチ送信してスコアを取得。
    - JSON Mode を利用し、レスポンスのバリデーション・スコアの ±1.0 クリップ・レスポンスパースの耐性（前後余分テキストの復元処理）を実装。
    - リトライ戦略：429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ。その他はスキップして継続するフェイルセーフ設計。
    - DuckDB の executemany のバージョン制約（空リスト不可）に配慮した DB 書き込み（DELETE → INSERT、部分失敗で既存データの保護）。
    - テスト容易性として `_call_openai_api` をパッチ差し替え可能に設計。
  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）を実装：
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で 'bull'/'neutral'/'bear' を判定。
    - ma200_ratio の計算（target_date 未満のデータのみ使用）とマクロ記事抽出、LLM（gpt-4o-mini）呼び出し、スコア合成、冪等な market_regime テーブル書き込みを実装。
    - 設計上、datetime.today() 等を参照せずルックアヘッドバイアスを避ける実装。
    - API 呼び出しの失敗は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - OpenAI クライアント呼び出し関数は news_nlp とは別実装にしてモジュール結合を低減。

- 汎用設計上の注意点（全体）
  - ルックアヘッドバイアス回避のため、date 引数ベースの設計（datetime.today()/date.today() の直接参照を避ける）。
  - DuckDB を主要なストレージとして想定し、日付型・NULL の扱い、executemany の互換性等に配慮した実装。
  - API 呼び出し（OpenAI/J-Quants）に対するリトライ・バックオフ・フェイルセーフの実装。API キーは引数注入または OPENAI_API_KEY 環境変数から解決。
  - テスト容易性を考慮して、API 呼び出し部分を差し替え可能（patchable）に実装。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Removed
- 新規リリースのため該当なし。

---

参考（実装上の目立つポイント）
- OpenAI モデル: gpt-4o-mini を想定して JSON Mode を使用。
- DuckDB 0.10 系との互換性を考慮した実装（executemany の空リスト問題等）。
- 環境自動ロードはプロジェクトルートの検出に依存するため、配布後も CWD に依存せず動作する設計。自動ロード不要なケース向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。