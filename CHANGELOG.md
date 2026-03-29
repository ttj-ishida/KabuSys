# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルはコードベース（kabusys パッケージ）の実装内容から推測して作成したリリースノートです。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-03-29

初回公開リリース。主な機能群と実装の要点を以下に示します。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - __all__ で公開サブパッケージを定義: data, strategy, execution, monitoring。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装:
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込みを実現。
    - 読み込み順序: OS 環境 > .env.local（上書き）> .env（非上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の行パーサーを実装（コメント、export プレフィックス、クォート／エスケープに対応）。
  - 環境変数必須チェック用の _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、実行環境、ログレベル等）。
  - 環境設定の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の値検証）およびユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST の記事を対象）を実装（calc_news_window）。
    - バッチ処理（1APIコールあたり最大 20 銘柄）・1銘柄あたりの最大記事数・文字数トリム処理を実装。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証（JSON 抽出、results リスト検証、未知コード除外、数値検証、±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）を実行し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し点を _call_openai_api として抽象化（unittest.mock.patch で差し替え可）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して MA200 乖離・マクロニュース抽出を実行し、OpenAI で macro_sentiment を推定。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）・再試行ロジックを実装。
    - レジーム算出値のクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しの独立実装によりモジュール結合を抑制。

- データ基盤ユーティリティ（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データが無い場合は曜日ベースでフォールバック（週末は休み）。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェック（過度に将来日付を検出した場合のスキップ）を実装。
  - ETL パイプライン補助（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーメッセージ等を集約）。
    - 差分更新やバックフィルの方針、品質チェックとの連携設計を反映したユーティリティ関数群（テーブル存在チェック、最大日付取得など）。

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高変化率）、バリュー（PER、ROE）の計算関数を提供。
    - DuckDB 内 SQL を活用して営業日ベースの窓処理を実装。データ不足時は None を返す安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズンに対応、入力検証あり）。
    - IC（Information Coefficient）算出（スピアマンのランク相関、欠損取り扱い、最小サンプル数チェック）。
    - ランク付けユーティリティ（rank: 同順位は平均ランク）。
    - 統計サマリー（count/mean/std/min/max/median）を計算する factor_summary。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーの取り扱いは環境変数（OPENAI_API_KEY）または関数引数で行う。キー管理は利用者側で適切に行うこと（ライブラリ側での保存は行わない）。

---

## 重要な注意事項 / 制約 / 今後の検討点（実装上の備考）
- OpenAI 連携
  - デフォルトモデルは gpt-4o-mini を想定。API 呼び出しは JSON Mode を利用する設計。
  - API 利用時は環境変数 OPENAI_API_KEY の設定が必須（関数引数から注入可能）。
  - API エラーは基本的にフェイルセーフでスキップまたはデフォルト値にフォールバックし、ETL 全体を停止させない設計。
- DB（DuckDB）
  - DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）に依存するため、運用前にスキーマ準備が必要。
  - DuckDB の executemany に空リストを渡せないバージョン対応のため、空チェックを明示的に行っている。
- 日付・時刻の扱い
  - 内部では timezone-naive の UTC または date を前提に設計（JST ↔ UTC の変換は明示的に行う）。運用環境での時刻取り扱いに注意。
- テスト容易性
  - OpenAI 呼び出しポイントを差し替え可能にしており、ユニットテストでのモック化を想定。
- 欠落データの取り扱い
  - データ不足時は None を返す、または中立値（例: ma200_ratio=1.0、macro_sentiment=0.0）にフォールバックする実装ポリシー。
- 追加検討事項
  - PBR・配当利回りなどバリュー指標の拡張、パフォーマンス最適化（大量銘柄処理時のチャンク戦略、並列化）、OpenAI 呼び出しのコスト制御など。

---

作成者注: 本 CHANGELOG は提供されたソースコードの内容とコメント（docstring、実装注釈）に基づき推測してまとめたものです。実際のリリースノートとして利用する場合は、実プロジェクトのコミット履歴やリリース時の変更点と照合してください。