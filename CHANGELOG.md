# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定版リリース以外の開発中の変更は Unreleased にまとめています。

現在のバージョン: 0.1.0 — 2026-03-29

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買・データ基盤および研究用ユーティリティの基盤機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージのメタ情報とエクスポートを追加（__version__ = 0.1.0, __all__）。
- 環境設定
  - 環境変数 / .env 読み込みユーティリティを追加（kabusys.config）。
    - プロジェクトルート自動検出（.git / pyproject.toml を探索）により CWD に依存しない .env 自動読み込み。
    - .env と .env.local の優先順位管理（OS 環境変数の保護機構を備えた override 処理）。
    - export 形式、クォート、インラインコメント対応のパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスを追加し、J-Quants・kabuステーション・Slack・DBパス・実行環境・ログレベル等の取得・バリデーションを提供。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック。
    - Path 型での duckdb/sqlite パス解決。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）の JSON mode でバッチ評価。
    - バッチサイズ、文字数上限、記事数制限、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンス検証ロジック（JSON 抽出・構造/型チェック・スコアのクリップ）。
    - DuckDB へ冪等的に書き込む処理（該当コードのみ DELETE → INSERT）を実装。
    - テスト向けに _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
    - マクロ記事抽出、OpenAI 呼び出し、指数的バックオフ、API エラーに対するフォールバック（macro_sentiment=0.0）を実装。
    - DuckDB トランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み。
    - LLM 呼び出し部分は news_nlp と独立実装（モジュール結合の低減）。
- データモジュール（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を追加（取得件数、保存件数、品質問題、エラー等を集約）。
    - 差分取得・バックフィル・品質チェックに関する設計方針を反映。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - ETL インターフェース再エクスポート（kabusys.data.etl）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する calendar_update_job を実装（バックフィル、健全性チェック、冪等保存）。
    - DB にデータが無い場合は曜日ベースでフォールバックする堅牢なロジック。
- 研究モジュール（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR）、バリュー（PER, ROE）等のファクター計算関数を実装。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman rank）、rank（平均ランク処理）、factor_summary（統計量）を実装。
  - 研究系ユーティリティの公開（__all__）を追加。
- ロギング/堅牢性
  - 多数の logger.debug/info/warning/exception を追加し、フェイルセーフおよびデバッグしやすい出力を整備。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を主要処理で参照しない設計（target_date を明示的に渡す方式）。
  - DuckDB の executemany による空リストバインド問題への対処（空時は呼ばない）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の読み込みで OS 環境変数を保護する protected セット機能を追加（.env による既存 OS 環境の上書きを防止）。

### Design / Implementation Notes
- OpenAI 呼び出しは JSON mode を利用し、レスポンスの厳密なパースと検証を行うことで LLM の出力ばらつきに耐性を持たせています。
- API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY をフォールバックで参照します。未設定時は ValueError を送出して早期検出。
- DB 書き込みは可能な限り冪等化（既存レコード削除→挿入）しており、部分失敗時に既存データを不必要に消さない設計です。
- DuckDB を前提とした実装で、日付値の取り扱い・互換性に注意したユーティリティを備えています。
- テスト容易性のため、外部 API 呼び出し（OpenAI etc.）を差し替え可能に設計しています（内部関数をパッチしてモック化）。

---

今後の予定（例）
- ETL の具体的な API クライアント実装（jquants_client の詳細実装・テストカバレッジ拡充）。
- 研究モジュールのさらなるファクター追加・パフォーマンス最適化。
- monitor / execution 等の自動売買実行モジュールの実装（パッケージ __all__ にはプレースホルダがあるため今後追加予定）。

（必要であれば、この CHANGELOG を英語版に翻訳したり、より細かいコミット単位の履歴に分解して追記できます。）