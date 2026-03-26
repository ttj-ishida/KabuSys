# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

フォーマット:
- すべての変更はセマンティックバージョニングに従います。
- 各リリースごとに Added / Changed / Fixed / Deprecated / Removed / Security のセクションを可能な限り分けて記載します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買・データ分析プラットフォームの基礎機能を実装しました。
主な特徴は以下の通りです。

### Added
- パッケージ全体
  - kabusys パッケージの初期公開。__version__ = "0.1.0"。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（プロジェクトルート自動検出: .git / pyproject.toml を基準）。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント取り扱い）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - Settings クラスを提供し、必要な設定をプロパティとして取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - 設定値のバリデーション（KABUSYS_ENV の許容値チェック、LOG_LEVEL の検証など）。
  - 必須環境変数未設定時にわかりやすい ValueError を送出。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを取得して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数の上限トリム設計（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフによるリトライ。レスポンスバリデーション（JSON 抽出、results キー/型/コード検証、スコア数値化）を実装。
    - 部分失敗に備え、DB への置換は対象コードのみ DELETE → INSERT で実施（既存スコア保護）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。

  - 市場レジーム判定（score_regime）
    - ETF 1321（TOPIX 等に対応するETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime_label（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出のためのキーワードリストを定義し、対象タイトルを最大件数で取得。
    - OpenAI 呼び出しに対してリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - レジームスコアのクリップおよび閾値設定（_BULL_THRESHOLD, _BEAR_THRESHOLD）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン。失敗時は ROLLBACK の試行と例外伝播。

- データ関連（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar テーブルが未取得の場合は曜日ベースのフォールバック（週末除外）。
    - next/prev_trading_day 等は DB 登録値を優先しつつ未登録日は曜日フォールバックで一貫性を保つ。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、先読み、健全性チェックを実装）。

  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーサマリを格納）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映したユーティリティ（最終取得日の計算、テーブル存在チェック等）。
    - jquants_client 経由での取得・保存処理との連携を想定したインターフェース。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、ma200 乖離を算出。データ不足時は None を返す仕様。
    - ボラティリティ・流動性（calc_volatility）: 20日 ATR（true_range の NULL 制御含む）、相対 ATR、20日平均売買代金、出来高比率。
    - バリュー（calc_value）: raw_financials から直近財務情報を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB の SQL ウィンドウ関数を多用して効率的に集計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の fwd リターンを一括取得。
    - IC 計算（calc_ic）: スピアマンのランク相関（ランクは平均ランクの取り扱い、最小レコード数 3）。
    - ランキングユーティリティ（rank）: 同順位は平均ランク、丸めによる ties の検出対策。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - pandas 等外部ライブラリに依存しない純 Python 実装を目指す。

- 基盤技術
  - DuckDB を主要なオンディスク分析 DB として利用。
  - OpenAI の Chat Completions（JSON mode）を利用する設計（gpt-4o-mini をデフォルトモデルとして指定）。
  - ルックアヘッドバイアス防止のため、内部処理では datetime.today() / date.today() を過度に参照しない設計方針を採用（target_date ベースで処理）。

### Changed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

### Deprecated
- 該当なし（初回リリース）

### Removed
- 該当なし（初回リリース）

### Security
- OpenAI API キー・各種シークレットは環境変数経由で取得する設計。必須変数未設定時は明示的にエラーを出す。

### Notes / 補足
- OpenAI への HTTP エラーや JSON パースエラーは多くの箇所でフェイルセーフ（スコア 0.0 を返す、あるいは対象コードをスキップ）になっており、外部 API 障害時でもパイプライン全体が停止しない設計になっています。
- DB 書き込みは部分的な置換（対象コードのみ DELETE → INSERT）やトランザクションを用いることで冪等性と既存データ保護を重視しています。
- テスト用フック（内部 _call_openai_api の差し替え等）を用意し、ユニットテストでのモックが容易になっています。

---

（注）この CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートや公開日、細かな互換性情報はプロジェクトのリリース運用方針に合わせて調整してください。