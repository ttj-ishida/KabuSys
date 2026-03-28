# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

### 注記
- 現在のリポジトリ状態は初期公開向けの機能群を含みます。将来的なリファクタリングや API 安定化により挙動が変わる可能性があります。

---

## [0.1.0] - 2026-03-28

初回公開リリース。

### Added
- パッケージ基本設定
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン定義（__version__ = "0.1.0"）。
  - パッケージ公開対象のモジュール構成を定義（data, strategy, execution, monitoring を __all__ に設定）。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は __file__ の親ディレクトリから .git または pyproject.toml を探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを実装（コメント行・export プレフィックス・クォート内のバックスラッシュエスケープ・インラインコメント処理をサポート）。
  - .env 読み込みの override/protected 制御を実装（OS 環境変数を保護する仕組み）。
  - Settings クラスを追加し、必要な環境変数をプロパティとしてアクセス可能に。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）。
    - env と log_level に対する許容値チェック（不正値は ValueError）。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事/文字数上限、JSON mode 出力のバリデーション・クリッピング（±1.0）を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ、フェイルセーフ（失敗時は該当チャンクをスキップ）を実装。
    - テスト容易化のため API 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ/フェイルセーフ・ルールを実装。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() 参照禁止）。

- Data（ETL / カレンダー / パイプライン）
  - ETL 結果型 ETLResult を公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）。
    - ETL 実行で収集されるメトリクス（取得数、保存数、品質問題、エラー概要など）を構造化して返す dataclass を提供。
    - DuckDB を想定したテーブル存在チェック・最大日付取得ユーティリティを実装。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を基にした営業日判定・次/前営業日算出・期間内営業日リスト取得・SQ 判定を実装。
    - DB にデータがない場合は曜日ベースでのフォールバック（週末を休日とする）。
    - calendar_update_job を実装（J-Quants から差分取得して保存、バックフィル、健全性チェック、冪等保存のフロー）。
  - ETL パイプラインの設計方針を実装（差分更新、backfill、品質チェック連携を想定）。

- Research（ファクター計算・特徴量探索）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）などの計算関数を提供。
    - DuckDB SQL を用いた効率的な集約クエリ実装。データ不足時の None 処理。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、rank（タイの平均ランク処理）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。入力検証（horizons 範囲等）あり。

- 共通実装/運用面
  - DuckDB を想定した SQL 実装、トランザクション（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK の取り扱いを多数の処理で採用（部分失敗時の保護設計）。
  - ロギングを多用し、API エラー時やデータ不足時に警告・情報ログを出力。
  - ルックアヘッドバイアス対策を設計指針としてドキュメント化・実装（datetime.today() の不使用、target_date ベース処理）。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を投げて明示的に失敗させる仕様。

### Notes / Implementation details
- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用して厳密な JSON 出力を期待する。ただし実運用での JSON 破損に備えた復元処理やパース失敗時のフォールバック（0.0 やスキップ）が実装されています。
- DuckDB のバージョン差異（executemany に空リスト渡せない等）を考慮した実装（空リスト時の実行回避）を行っています。
- テスト容易性を考慮し、外部 API 呼び出し箇所（_call_openai_api）をパッチで差し替え可能にしています。
- 設計方針として「本番口座・発注 API には一切アクセスしない」ことを明記し、データ処理・リサーチ機能の分離を徹底しています。

---

メジャー/マイナー/パッチの次のリリースでは以下を検討してください（例）:
- strategy / execution / monitoring の実装追加や公開 API の安定化
- 単体テスト・統合テスト・CI パイプラインの整備
- ドキュメント（Usage examples / API リファレンス）の充実
- セキュリティ向上のための秘密情報ハンドリング改善（シークレット管理連携など）