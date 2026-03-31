# Changelog

すべての注記は Keep a Changelog の形式に従い、重要度を「Added / Changed / Fixed / Security / Deprecated / Removed」に分類しています。  
日付とバージョンは、ソース内のバージョン情報（__version__ = "0.1.0"）および本ファイル作成日（YYYY-MM-DD）に基づいています。

なお、実際のコミット履歴がないため、以下はリポジトリ内のコード構成・実装内容から推測して作成した初回リリース向けの変更履歴（概要）です。

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - 公開モジュール: data, strategy, execution, monitoring（__init__ でエクスポート）

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）
  - export 形式やクォート・エスケープ・インラインコメントへの対応を含む .env 行パーサ実装
  - .env.local を .env 上書き（override）する仕組み、OS 環境変数保護（protected set）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供し、各種必須設定値（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル）をプロパティで取得
  - 値検証（env, log_level 等の許容値チェック）と必須値未設定時の明示的なエラー

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング（`news_nlp.score_news`）
    - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコア生成
    - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30）計算ユーティリティ `calc_news_window`
    - バッチ処理（銘柄ごと最大 20 件バッチ）とトークン肥大化対策（記事数・文字数トリム）
    - JSON Mode のレスポンス検証・復元（前後ノイズの { ... } 抽出対応）および詳細バリデーション
    - API エラー（429・接続断・タイムアウト・5xx）での指数バックオフリトライ
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に実装

  - 市場レジーム判定（`ai.regime_detector.score_regime`）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定
    - マクロニュースフィルタ（キーワード群）による記事抽出、LLM による -1〜1 のセンチメント評価
    - API リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）およびレスポンスパース保護
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス対策（target_date 未満のデータのみを参照、datetime.today() を参照しない設計）

- Data モジュール（`kabusys.data`）
  - マーケットカレンダー管理（`data.calendar_management`）
    - JPX カレンダーの夜間バッチ更新ジョブ (`calendar_update_job`)
    - 営業日判定ユーティリティ群: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - DB 未取得時は曜日ベース（平日＝営業日）でのフォールバック
    - 最大探索日数やバックフィルなど健全性チェックと運用上の設計考慮

  - ETL パイプライン（`data.pipeline` / `data.etl`）
    - 差分取得、保存、品質チェックを想定した ETLResult データクラスを公開（`ETLResult` を `data.etl` で再エクスポート）
    - 最小データ日やデフォルトバックフィル日などのデフォルト挙動を定義
    - DuckDB 上での最大日付取得やテーブル存在確認ユーティリティを実装

- Research モジュール（`kabusys.research`）
  - ファクター計算（`research.factor_research`）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）を計算する関数を実装
    - DuckDB 上での SQL ベース処理で営業日ベースの取り扱いに配慮
  - 特徴量探索ユーティリティ（`research.feature_exploration`）
    - 将来リターン計算（`calc_forward_returns`）、IC（`calc_ic`）、ランク付け（`rank`）、統計サマリー（`factor_summary`）を実装
    - 外部ライブラリに依存しない純標準ライブラリ実装

### Changed
- API 呼び出し周りの堅牢性向上
  - OpenAI 呼び出しでの JSON Mode を利用し、レスポンスパースの耐性（余計な前後テキストや型の揺らぎを許容）を実装
  - API エラーの分類に基づくリトライロジック（RateLimit/接続/タイムアウト/5xx はリトライ、それ以外は即スキップ）を導入
  - retry/backoff の設定定数化（_MAX_RETRIES, _RETRY_BASE_SECONDS）

- DuckDB に対する書き込み処理の耐性
  - 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護
  - 部分失敗時にも既存データを不必要に削除しないために、書き込み対象コードを絞って DELETE → INSERT を実行
  - DuckDB 互換性対策（executemany に空リストを渡さないガード）

- 日付・時間周りの設計方針を一貫化
  - ルックアヘッドバイアス防止のため、target_date 以外に datetime.today()/date.today() を直接参照しない実装を採用（外部から target_date を注入する設計）

### Fixed
- ニュースレスポンスパースの堅牢性改善
  - JSONDecodeError が発生するケースで、文字列内から最外の { ... } を抽出して再パースするロジックを追加
  - レスポンス内のスコアやコードが期待型でない場合でもスキップして他の銘柄に影響を与えないように改良

- エッジケース対応
  - MA200 計算などでデータが不足する場合に中立値（1.0 など）を返すことで処理継続を可能に（警告ログ発行）
  - news_nlp / regime_detector において記事が存在しない場合は LLM 呼び出しをスキップして安全に継続

- calendar / trading day ロジックの堅牢化
  - market_calendar が部分的にしか入っていない場合でも next_trading_day / prev_trading_day / get_trading_days が一貫した挙動になるよう DB 値優先＋曜日フォールバックで実装
  - カレンダーの last_date が極端に将来値の場合は健全性チェックで処理をスキップしログ出力

### Security
- 特になし（公開コードから推測される範囲での変更履歴）

### Deprecated
- なし（初回リリースと想定）

### Removed
- なし（初回リリースと想定）

---

注意:
- 上記はコードベースの実装内容から推測して作成した CHANGELOG です。実際の変更履歴（コミットメッセージやリリースノート）とは差異があり得ます。必要であれば、各モジュールに対するより詳細なリリースノート（関数ごとの変更点、パラメータ仕様、既知の制約や既存の TODO）も作成できます。