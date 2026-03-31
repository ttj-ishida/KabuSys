# Changelog

すべての重要なリリース変更はこのファイルに記録します。フォーマットは「Keep a Changelog」仕様に準拠します。  
この CHANGELOG はコードベースの実装内容から推測して作成しています。

注意: バージョン番号はパッケージ内の __version__（0.1.0）に基づきます。

## [Unreleased]

（現時点での未リリース変更はありません）

## [0.1.0] - 2026-03-31

初回公開リリース。

### Added
- パッケージ骨格
  - kabusys パッケージを追加。サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ により公開）。
  - バージョン情報: __version__ = "0.1.0"。

- 設定・環境読み込み
  - 環境変数・設定管理モジュール（kabusys.config）を追加。
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で停止可能。
  - 複雑な .env パースの実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、
    - インラインコメントの取り扱いなど。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / 環境（development/paper_trading/live）やログレベルの検証を行う。

- AI（OpenAI）関連
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数上限・文字数トリム）。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスバリデーションを実装（JSON 抽出/検証、未知コード無視、スコアクリップ）。
    - DuckDB 互換性のための executemany 空リスト回避などの注意処理。
    - test 用に _call_openai_api を差し替え可能にしている（モックしやすい設計）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - マクロキーワードで記事をフィルタ、OpenAI 呼び出しは独立実装（モジュール結合低減）。
    - API エラー時はマクロスコアを 0.0 にフォールバック（フェイルセーフ）。
    - 再試行ロジックとログ出力を実装。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラーを格納）。
    - 差分取得、バックフィル、品質チェック（quality モジュールと連携）を想定した設計。
  - ETL の公開インターフェース (kabusys.data.etl) で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定・次営業日/前営業日・期間内営業日取得・SQ判定を提供。
    - market_calendar が未登録時は曜日ベース（土日非営業）でフォールバック。
    - カレンダー夜間更新ジョブ（calendar_update_job）を追加：J-Quants から差分取得して冪等で保存、バックフィルや健全性チェックを実装。
    - 最大探索日数やバックフィル日数など安全性パラメータを設定。
  - DuckDB による SQL 実行における各種ユーティリティ（テーブル存在確認、日付変換等）を実装。

- リサーチ用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1m/3m/6m リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高比）、バリュー（PER/ROE）を算出する関数を追加。
    - DuckDB 上の SQL とウィンドウ関数を活用して効率的に計算。
    - データ不足時の None 処理、戻り値は (date, code) をキーとした dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターンの計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient、Spearman ρ）計算。
    - ランク関数（平均ランクによる同順位処理）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - 外部ライブラリ不使用（標準ライブラリのみ）での実装。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を利用する設計。
- .env の読み込みはデフォルトで行うが、KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能。
- 自動上書き処理では OS 環境変数を保護する protected セットを導入。

### Notes / Limitations / Implementation details（実装上の重要な注意点）
- ルックアヘッドバイアス防止:
  - AI・リサーチ・ニュース関連関数は内部で datetime.today() / date.today() を参照せず、呼び出し側が target_date を与える設計。
  - DB クエリは target_date 未満 or 以前/以降などの排他条件を適切に使用。
- OpenAI 呼び出し:
  - JSON mode を使用し、レスポンスの厳密な JSON 期待するが、前後に余計なテキストが混入した場合の復元ロジックを導入。
  - レート制限・ネットワーク障害・サーバーエラーに対するリトライとバックオフを実装。非再試行エラーはスキップして処理を継続するフェイルセーフ方針。
- DuckDB 互換性:
  - executemany に空リストを渡せない等のバージョン依存問題に対応する防御的実装あり（空の場合は処理スキップ）。
- テスト容易性:
  - OpenAI 呼び出しラッパー（モジュール内 _call_openai_api）をパッチ/モックできるようにしている。
- 冪等性:
  - DB 書き込みは可能な限り冪等（DELETE→INSERT / ON CONFLICT 等）で実装し、部分失敗時のデータ保護を考慮している。
- フォールバック挙動:
  - market_calendar が未設定の場合は曜日ベースで日判定するなど、外部データ未取得時も稼働する設計。

---

今後の予定（推測）
- 監視・実行（execution / monitoring）や戦略（strategy）周りの詳細実装や CI、ドキュメントの拡充が想定されます。
- テストケースの追加（DuckDB fixtures、OpenAI モック等）、パフォーマンス最適化、型注釈の厳密化など。

（以上）