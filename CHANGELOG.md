# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。  

現在のバージョンは 0.1.0（初期リリース）です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

### 追加 (Added)
- 基本パッケージ構成を追加（kabusys パッケージ、バージョン: 0.1.0）。
  - src/kabusys/__init__.py: パッケージ公開モジュール一覧（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理機能を追加。
  - src/kabusys/config.py
    - .env および .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .git または pyproject.toml を基準にプロジェクトルートを検索（CWD に依存しない）。
    - 柔軟な .env パーサ実装（コメント、export 形式、クォート、エスケープ対応）。
    - 環境変数保護（OS 環境変数を protected として .env の上書きを制御）。
    - Settings クラスを提供し、J-Quants・kabu API・LINE・DB パス・監視設定・システム設定（KABUSYS_ENV, LOG_LEVEL）等をプロパティ経由で取得。
    - 必須キー未設定時は明示的な例外を投げるユーティリティ (_require)。

- AI（自然言語処理）モジュールを追加。
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を統合して OpenAI（gpt-4o-mini、JSON Mode）へ投げ、銘柄ごとのセンチメント（ai_score）を計算して ai_scores テーブルへ保存するワークフローを実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算のユーティリティ（calc_news_window）。
    - バッチ処理、トリム（文字数・記事数制限）、最大バッチサイズ、429/ネットワーク/5xx に対するエクスポネンシャルバックオフとリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON の復元、results 検証、コード正常化、スコアのクリップ）。
    - テストのために OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロキーワードによる記事フィルタリング、OpenAI 呼び出し、再試行ロジック、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - OpenAI クライアントは引数または環境変数 OPENAI_API_KEY から解決。

- データプラットフォーム用モジュールを追加。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - calendar_update_job を実装し、J-Quants から差分取得して冪等保存（バックフィルと健全性チェック付き）。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基本インターフェースを実装（差分取得、保存、品質チェックの呼び出し）。
    - ETLResult データクラスを導入し、取得/保存件数・品質問題・エラー情報を集約（to_dict を提供）。
    - DuckDB を前提としてテーブル存在チェックや最大日付取得ユーティリティを実装。
    - デフォルトのバックフィル挙動、カレンダー先読み等の設定を備える。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

  - src/kabusys/data/__init__.py: データパッケージの基礎（クライアント等は別モジュールとして想定）。

- 研究（Research）モジュールを追加。
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクター算出関数を実装。
    - DuckDB 上の prices_daily / raw_financials を利用する純粋な計算ロジック。
    - データ不足時は None を返す設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns）。
    - IC（Information Coefficient：Spearman の ρ）計算（calc_ic）。
    - 値をランクに変換するユーティリティ（rank）。
    - ファクター統計要約（factor_summary）。
    - research パッケージの __init__.py で主要関数を再エクスポート。

### 仕様・設計上の注意 (Notes)
- ルックアヘッドバイアス回避
  - AI モジュール・研究モジュール等は内部で datetime.today()/date.today() を参照せず、呼び出し側から与えられる target_date を基準に処理する設計になっています。過去データのみを参照するよう厳格に実装されています。

- データベース操作は冪等性を重視
  - market_regime, ai_scores, 各保存処理は既存レコードの削除→挿入や ON CONFLICT 相当のロジックで冪等にデータ更新を行います。部分失敗時に他のコードの既存データを保護するため、対象コードを限定して DELETE/INSERT を行います。

- OpenAI（gpt-4o-mini）連携
  - JSON Mode を利用し、出力のパースを行う。API エラー（429, ネットワーク断, タイムアウト, 5xx）には指数的バックオフでリトライし、最終的にフェイルセーフ動作（0.0 スコアやスキップ）を行います。
  - テスト容易性のため、内部の API 呼び出し関数は patch できるように分離しています。

- DuckDB を前提とした SQL 実装
  - windowed 関数（OVER）や executemany の挙動（空リスト制限）等、DuckDB の実装特性を考慮した実装になっています。

- .env パーシングの堅牢化
  - export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。既存の OS 環境変数を保護する仕組みを提供。

### 修正 (Fixed)
- 初回リリースのため特段の bugfix はなし（設計段階で上記フェイルセーフやフォールバックを実装）。

### 変更 (Changed)
- 初回リリース: N/A

### 非推奨 (Deprecated)
- 初回リリース: N/A

### セキュリティ (Security)
- 環境変数に機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を要求します。これらは .env に格納するか環境変数として安全に管理してください。
- 自動 .env 読み込みはテスト等で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

注: この CHANGELOG はコードベースの実装内容から推測して作成した初期リリースの概要です。実際のリリースノート作成時にはリリース日や追加の変更点（依存関係、ビルド手順、既知の制限や既知の issue）を合わせて記載してください。