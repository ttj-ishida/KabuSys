# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から推測して作成しています（実装上の意図・設計方針を要約）。

全般的なバージョニング規約: セマンティックバージョニングを想定。

## [Unreleased]
（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装。

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ: kabusys（src/kabusys）
  - エクスポート: data, strategy, execution, monitoring を __all__ に定義
  - バージョン: __version__ = "0.1.0"

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local または OS 環境変数から設定を自動読み込み
  - プロジェクトルート探索は __file__ を基準に .git または pyproject.toml を探索（CWD 非依存）
  - .env パーサを実装（export 形式、クォート／エスケープ、インラインコメント処理対応）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - 必須環境変数取得関数 _require を提供
  - Settings クラスを公開（J-Quants、kabuステーション、Slack、DB パス、実行環境判定など）
  - 許容値チェック（KABUSYS_ENV、LOG_LEVEL）

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - OpenAI（gpt-4o-mini）を用いたバッチ評価（JSON モード）
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 に対応）
    - 銘柄別に記事を集約して最大文字数・記事数でトリム
    - バッチサイズ、リトライ（指数バックオフ）、レスポンスバリデーションを実装
    - ai_scores テーブルへの冪等的な置換（DELETE → INSERT の方式）
    - エラーや API 異常時はフェイルセーフ（例外を投げずスキップ）で継続
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - OpenAI（gpt-4o-mini）呼び出し、再試行・フォールバックを実装
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス回避（内部で date.today() を直接参照しない、DB クエリに date < target_date を採用）
  - 公開 API: score_news, score_regime（テスト用に _call_openai_api をモック可能に設計）

- データプラットフォーム関連 (src/kabusys/data)
  - ETL パイプライン基盤 (pipeline.ETLResult を etl 経由で公開)
    - 差分更新・バックフィル・品質チェックのためのデータクラス ETLResult を実装
    - DB テーブル存在チェック、最大日付取得等のユーティリティ
  - カレンダー管理 (calendar_management.py)
    - market_calendar を元に営業日判定、next/prev trading day、SQ 判定、期間内営業日取得
    - J-Quants からの差分取得ジョブ calendar_update_job の骨組み（バックフィル、健全性チェック、保存処理呼び出し）
    - DB 未登録日のフォールバックは曜日ベース（土日非営業）
    - 最大探索日数制限で無限ループ防止
  - jquants_client 経由の ETL ワークフローと互換性を意識した設計（差分取得、idempotent 保存、品質管理連携）

- リサーチ（ファクター）モジュール (src/kabusys/research)
  - factor_research: ファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時の None 処理）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新レコードを取得）
    - DuckDB を用いた SQL 中心実装（prices_daily / raw_financials を参照）
  - feature_exploration: 特徴量解析ユーティリティ
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（LEAD を活用）
    - calc_ic: スピアマンランク相関（ランク計算は tie の平均ランクに対応）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 値のランク化（浮動小数点の丸め対策を実装）
  - research パッケージから主要関数を再エクスポート

- データユーティリティ
  - data.etl が pipeline.ETLResult を再公開
  - DuckDB を前提とした SQL 実装と互換性配慮（DuckDB 0.10 の executemany の挙動を考慮した空リストチェック等）

- ロギングと堅牢性
  - 各処理で詳細な logger 呼び出しを実装（info/debug/warning/exception）
  - 外部 API 呼び出しに対する再試行、5xx と非 5xx の扱い分離、タイムアウト対応
  - JSON レスポンスの耐障害性（前後余計テキストの復元、キー存在チェック、型チェック）
  - DB 書き込みでの BEGIN/COMMIT/ROLLBACK を利用した冪等性確保とロールバック時の警告ログ

### 変更 (Changed)
- N/A（初期リリースのため過去からの変更なし）

### 修正 (Fixed)
- N/A（初期リリース。ただし設計上多くのフォールバック / エラーハンドリングが実装されている点を記載）

### 既知の制限 / 未実装 (Notes / Known limitations)
- news_nlp.calc_news_window の時間ウィンドウは JST を基準に UTC naive datetime を返す設計（利用側でのタイムゾーン注意）
- calc_value: PBR・配当利回りは未実装（コメントで明記）
- OpenAI 依存: score_news / score_regime は OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）
- DuckDB 前提: 実装は DuckDB を前提としている（他 DB での互換性は未検証）
- 一部の DB バインド・executemany の実装は DuckDB バージョン差分に注意（空リスト禁止回避ロジックを導入）
- AI モジュールは JSON Mode を前提としているが、LLM 出力の不確実性に備えた復元・パース保護を実装している

### セキュリティ (Security)
- N/A（リリース当時に公開済みセキュリティ修正はなし）

---

開発・設計上の注記:
- ルックアヘッドバイアス回避のため、date.today() をアルゴリズム内部で直接参照しない実装方針を一貫して採用。
- 外部 API 呼び出しはフェイルセーフ戦略を採用（API エラー時はスコアを 0.0 にフォールバック、処理継続）。
- テスト容易性を配慮し、OpenAI 呼出し部分は内部関数をモック可能に実装。

（この CHANGELOG はコードから推測して作成した概要です。実際のリリースノートはリポジトリの変更履歴やコミットログを参照して更新してください。）