# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。  

## [0.1.0] - 2026-04-01

初回リリース — 日本株自動売買システム "KabuSys" の基盤機能を実装しました。主に以下の機能群を提供します。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
  - .env 解析は以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - 行末コメント（クォート外かつ直前が空白/タブの場合）の扱い
  - 上書き制御（override）と protected（OS 環境変数の保護）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル等を環境変数から取得するプロパティを実装。
  - 環境値の検証:
    - KABUSYS_ENV は development / paper_trading / live のみ許容。
    - LOG_LEVEL は標準ログレベルのみ許容。
  - Path を返す設定値は expanduser を行う（~ の展開）。

- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news と news_symbols を元に銘柄別ニュース集約と OpenAI（gpt-4o-mini）によるバッチセンチメント評価を実装。
  - タイムウィンドウ計算（JST: 前日 15:00 ～ 当日 08:30）を calc_news_window で提供。
  - チャンクバッチ処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数トリム制限を実装。
  - OpenAI への呼び出しは JSON Mode を使用。429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
  - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップを実装（不正レスポンスは安全にスキップ）。
  - DuckDB への書き込みは部分的な失敗に備え、スコア取得済みのコードのみ DELETE → INSERT で置換する（部分失敗時に既存データを保護）。
  - テストしやすさのため、OpenAI 呼び出し箇所はパッチ可能（_call_openai_api をモック可能）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離とニュースのマクロセンチメントを重み合成して日次レジーム（bull/neutral/bear）を判定。
  - ma200 比率計算、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価を実装。
  - スコア合成ロジック（重み 70%:MA, 30%:macro）、閾値によるラベル付与を実装。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行し例外伝播。
  - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を用いて PER/ROE を計算（EPS 無効時は None）。
    - すべて DuckDB の prices_daily / raw_financials のみを参照し、外部 API へのアクセスは行わない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル数不足時は None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク変換実装。
  - 研究用ユーティリティの公開 (zscore_normalize を data.stats から再エクスポート)。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理、営業時間判断ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB の market_calendar を優先し未登録日は曜日ベース（平日）でフォールバックする一貫性のあるロジック。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・保存を行う処理を実装（健全性チェックあり）。
  - pipeline / ETL:
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した ETL 設計。
    - jquants_client 経由の idempotent 保存を想定。
  - etl モジュールは公開インターフェースとして ETLResult を再エクスポート。

### 変更 (Changed)
- 設計方針（全体）
  - 多くの処理で datetime.today() / date.today() を直接参照しない設計に統一（target_date 引数依存）。ルックアヘッドバイアス防止のため。
  - OpenAI 呼び出し部分はモジュール間でプライベート関数を共有しない（news_nlp と regime_detector で独立実装）ことでモジュール結合を低減。
  - DuckDB のバージョン差異（executemany に空リスト不可など）を考慮した互換性対策を実装。

### 修正 (Fixed)
- API 失敗時の安全化
  - OpenAI の各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError(5xx)）に対してリトライ/フォールバック処理を実装し、フェイルセーフ（ゼロスコアやスキップ）で継続できるようにした。
- .env 読み込みの堅牢化
  - 存在しないファイルの扱いやファイルオープン失敗時に warnings を発行して処理継続するように。

### 既知の注意点 / 制約 (Known issues / Limitations)
- OpenAI のレスポンスは JSON Mode を期待するが、稀に前後に余計なテキストが混ざる場合のために最外の { ... } を抽出するフォールバックを実装している（完璧ではない）。
- DuckDB バインド挙動はバージョン差による影響を受ける可能性があるため、executemany 周りで互換性対策をしている。
- calendar_update_job の J-Quants 呼び出しおよび保存処理は jquants_client の実装に依存する。API エラー時はジョブは 0 を返す。

### セキュリティ (Security)
- 特に追加のセキュリティ修正はありません。API キーは環境変数（OPENAI_API_KEY 等）で供給する設計。環境変数の自動読み込みは必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

今後の予定（例）
- strategy / execution / monitoring サブパッケージの詳細実装（アルゴリズム・発注ロジック・監視アラート）。
- テストカバレッジの拡充（特に OpenAI 呼び出しのモックを用いた統合テスト）。
- jquants_client や kabu_api の具体的実装との結合テスト及び API エラー処理の強化。