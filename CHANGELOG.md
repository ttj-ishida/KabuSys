# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の書式に従い、セマンティックバージョニングを採用します。  
日付は YYYY-MM-DD 形式を使用します。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買およびリサーチ / データ基盤向けのコア機能を提供します。

### 追加 (Added)
- パッケージ概要
  - kabusys パッケージの初期公開。__version__ = 0.1.0。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパースは export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などをサポート。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護: OS 環境変数を保護するための上書き制御（protected keys）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の設定プロパティを公開（必須項目は未設定時に ValueError を発生）。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を元に「前日 15:00 JST 〜 当日 08:30 JST」のウィンドウでニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価して銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - バッチ処理: 1 API 呼び出しにつき最大 20 銘柄。
    - 1 銘柄あたり最大記事数・文字数（トリム）制御を実装（記事数上限: 10、文字上限: 3000）。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフとリトライを実装。リトライ後も失敗したチャンクはスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー／型検査、未知コードの無視、数値チェック、スコアクリップ ±1.0）。
    - 書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
    - datetime.today()/date.today() に依存しない設計でルックアヘッドバイアスを回避。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロニュースセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは指定キーワードでフィルタ。LLM 呼び出しは gpt-4o-mini（JSON 出力）で行い、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - OpenAI クライアント呼び出しはサブルーチン化され、テスト時に差し替え可能。
    - ルックアヘッドを防ぐクエリ条件を厳密に設計。

- データ / ETL モジュール (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする堅牢な挙動。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数／ルックアヘッド／バックフィル日数等の安全制約を設定。
  - pipeline (ETL):
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラー等を集約）。
    - 差分取得、バックフィル、品質チェックを行う ETL の基本設計（jquants_client との連携想定）。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、market_calendar を考慮したトレーディングデイ調整等を実装。
  - etl モジュールは ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比）などの計算関数を実装（calc_momentum / calc_value / calc_volatility）。
    - DuckDB を用いた SQL ベース実装。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、最大 252 営業日チェック）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）、値をランクに変換する rank ユーティリティ、ファクター統計 summary（factor_summary）を提供。
    - 実装は標準ライブラリのみを使用し、pandas 等に依存しない。

- 共通実装上の注意点（設計方針）
  - ルックアヘッドバイアス防止のため、各モジュールは date / target_date を明示的に受け取り、内部で datetime.today() を参照しない。
  - DuckDB を主要なローカルデータベースとして使用。書き込みは可能な限り冪等性を保つ（DELETE→INSERT または ON CONFLICT 方式）。
  - OpenAI 呼び出し周りはリトライ・タイムアウト・JSON モード対応など堅牢化。
  - テスト容易性のため、内部 API 呼び出し（_call_openai_api 等）は patch で差し替え可能。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- なし（初回リリース）。

---

注: この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース担当の記録を合わせて更新してください。