# CHANGELOG

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

- 準拠バージョン: 0.1.0（初回リリース）
- リリース日: 2026-03-28

## [Unreleased]
- 現在、未リリースの変更はありません。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース。
- 基本メタ情報:
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - 主要サブパッケージをトップレベル __all__ で宣言。

- 環境設定管理 (`kabusys.config`):
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を基準に __file__ から親ディレクトリを探索（配布後の動作を想定）。
  - .env パーサー実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - インラインコメントや '#' の扱いに配慮した振る舞い。
  - .env 読み込み関数で既存 OS 環境変数を保護する `protected` 機構。
  - `Settings` クラスを提供し、アプリケーションで必要な設定値（J-Quants / kabuAPI / Slack / DB パス / 環境モード / ログレベル等）をプロパティ経由で取得可能。環境値のバリデーション実装（KABUSYS_ENV, LOG_LEVEL）。

- AI モジュール (`kabusys.ai`):
  - ニュースセンチメントスコアリング (`news_nlp.score_news`):
    - 前日 15:00 JST ～ 当日 08:30 JST の記事ウィンドウ集計（UTC 変換を内部で正確に扱う）。
    - raw_news と news_symbols テーブルを結合して銘柄ごとに記事を集約（最新 N 件・文字数トリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/チャンク）。JSON Mode を期待。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライ。
    - レスポンス検証（JSON 抽出、results リスト・code/score 検証、数値変換、クリップ ±1.0）。
    - DuckDB 互換性考慮: executemany に空リストを渡さない防御ロジック。
    - フェイルセーフ: API 失敗時はスキップ継続。スコア取得済みコードのみ置換（部分失敗時に他銘柄データを保護）。
  - 市場レジーム判定 (`ai.regime_detector.score_regime`):
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で 'bull' / 'neutral' / 'bear' 判定を行う。
    - マクロニュース抽出はキーワードベース（複数言語・日米キーワード含む）。
    - OpenAI 呼び出しは専用関数を使用しリトライを実装。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は冪等に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時はロールバックを実施。
    - ルックアヘッドバイアスを防ぐため、target_date 未満のデータのみ参照し、datetime.today() を参照しない設計。

- リサーチモジュール (`kabusys.research`):
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）等の定量ファクター計算関数を提供。
    - DuckDB SQL と純 Python 組合せで実装。prices_daily / raw_financials のみ参照し外部 API に依存しない。
    - データ不足時の扱い（None を返す）やログ出力を明示。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - ties（同順位）を平均ランクで扱う安定実装。horizons の妥当性チェックを実装。
    - pandas 等に依存しない純標準ライブラリ実装。

- データプラットフォームモジュール (`kabusys.data`):
  - カレンダー管理 (`data.calendar_management`):
    - JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）を実装。J-Quants API から差分フェッチし market_calendar テーブルへ冪等保存（ON CONFLICT 相当）。
    - バックフィルや健全性チェック（極端な未来日付検出）を実装。
    - 営業日判定ユーティリティ群: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB 登録値優先、未登録日は曜日ベースのフォールバックで一貫性を確保。
    - 最大探索日数制限を導入し無限ループを防止。
  - ETL パイプライン (`data.pipeline` / `data.etl`):
    - ETLResult データクラスを公開し、ETL の取得件数・保存件数・品質チェック結果・エラーを集約できるようにした。
    - ETL 実装方針に沿った差分更新、backfill、品質チェックの設計（jquants_client と quality モジュールを利用する想定）。
    - data.etl は pipeline.ETLResult を再エクスポート。
  - jquants_client など外部クライアントとのインターフェースを想定した実装（fetch/save の呼び出し箇所を用意）。

- モジュール公開の整理:
  - ai/__init__.py, research/__init__.py 等で主要関数を __all__ で再公開し利用しやすくした。

### Changed
- （初回リリースのため該当なし）

### Fixed
- DuckDB 使用上の互換性問題に留意した実装:
  - executemany に空リストを渡すとエラーとなるバージョンに対して、事前チェックを追加（空の場合は実行しない）。
- LLM レスポンスの JSON 解析に対する堅牢性向上:
  - JSON Mode でも前後に余計なテキストが混入する可能性を想定し、最外の {} を抽出して復元する処理を追加。
- API エラー処理:
  - OpenAI API の各種例外（RateLimitError/APIConnectionError/APITimeoutError/APIError）ごとにリトライ/フォールバック方針を明確化し、非 5xx エラーは即スキップ、5xx はリトライする挙動を採用。

### Security
- OpenAI API キーや各種トークンは Settings 経由で環境変数から取得する設計。必須項目は未設定時に ValueError を投げて明示的に扱う。

### Notes / Implementation details
- ルックアヘッドバイアス対策として、全ての「日指定処理」は内部で datetime.today()/date.today() を直接参照しない（target_date を明示的引数に取る設計）。
- OpenAI に対する呼び出しはテスト容易性を考慮し、内部の API 呼び出し関数を patch 可能にしている（ユニットテストで差替え可能）。
- 各所で冪等性・部分失敗耐性（部分的に書き換える、既存データを不必要に消さない等）を優先した実装方針。
- ロギングを随所に配置し、異常系は警告/例外ログで追跡可能にしている。

---

今後のリリースでは以下のような改善候補が想定されます（例）:
- strategy / execution / monitoring モジュール群の実装・公開（トップレベル __all__ に宣言あり）。
- ai モデルやプロンプトのチューニング、レスポンス検証のさらなる強化。
- ETL の実働ジョブ化・監視・メトリクス収集機能追加。