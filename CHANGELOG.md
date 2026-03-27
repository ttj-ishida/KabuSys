# Changelog

すべての重要な変更点を列挙します。本ファイルは Keep a Changelog の形式に準拠します。  
このプロジェクトの初期公開リリースに向けて、コードベースから推測可能な追加・挙動・設計方針を記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし（現時点での次回作業領域）

## [0.1.0] - 2026-03-27
初回リリース。本バージョンは日本株向けの自動売買／調査プラットフォームの基礎機能を提供します。以下の主要機能・設計方針・品質改善点を含みます。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージ（__version__ = 0.1.0）と主要サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。
  - settings オブジェクト: 環境変数を型付きプロパティで取得する Settings クラスを導入。必須値取得時に未設定だと ValueError を送出する _require を提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を起点）から .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。クォート・コメント・export キーワードに対応する独自パーサを実装。
  - 設定例: J-Quants / kabuAPI / Slack / DB パス / 環境モード（development/paper_trading/live） / ログレベルなどをプロパティとして提供。

- データプラットフォーム関連（kabusys.data）
  - ETL パイプライン基盤: pipeline モジュールの ETLResult データクラスを公開（ETL 実行結果の集約、品質問題とエラーの記録）。
  - calendar_management: JPX マーケットカレンダーの管理（market_calendar 参照／更新）、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）、夜間バッチ更新 job（calendar_update_job）を実装。DB 未取得時の曜日ベースフォールバックや健全性チェック（過度の将来日付検出）を含む。
  - ETL 設計方針の反映: 差分取得、バックフィル、品質チェックフロー（quality モジュール連携想定）、idempotent な保存（jquants_client 経由の保存）など。

- 研究（research）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、ATR/価格比、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から直近財務を取得して PER, ROE を計算（EPS 欠損・ゼロ時は None）。
    - 設計: DuckDB の prices_daily / raw_financials を用いた SQL 集約 + Python 返却で副作用なし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト 1,5,21）を計算。ホライズン入力検証（1〜252）を実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード数が 3 未満なら None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count, mean, std, min, max, median）を提供。
  - research パッケージは主要関数を __all__ で公開（calc_momentum 等）。

- AI（kabusys.ai）
  - news_nlp:
    - news に対するバッチセンチメント評価機能（score_news）。前日 15:00 JST 〜 当日 08:30 JST のウィンドウを対象に raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）へ最大 20 銘柄/チャンクで送信、レスポンス検証を行って ai_scores テーブルへ書き込み。
    - 入力トリム（1銘柄あたり最大記事数 / 最大文字数）やレスポンスの検証（JSON パース、results 配列、コード整合性、数値性）を実装。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ（最大試行回数定義）。
    - フェイルセーフ: API 呼び出し失敗やレスポンス検証失敗はそのチャンクをスキップし、処理を継続する設計（部分失敗時に既存データを保護するため削除→挿入で対象コードのみ置換）。
    - テスト支援: _call_openai_api を patch 可能（unittest.mock.patch 推奨）。
  - regime_detector:
    - マーケット・レジーム判定（score_regime）。ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出（マクロキーワード）と LLM スコアリング、API エラー時のフォールバック（macro_sentiment=0.0）、リトライやログ出力を実装。
    - 設計方針: ルックアヘッドバイアス防止（datetime.today() を参照しない、prices_daily は date < target_date を使用）やモジュール結合低減（_call_openai_api を news_nlp と共有しない）を採用。

### Changed
- （初回公開のため該当なし）

### Fixed
- DB 書き込み安全性
  - ai_scores / market_regime への書き込みは トランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に処理し、例外時に ROLLBACK を試みる実装を追加。ROLLBACK が失敗した場合は警告ログを出す。
- API フォールバック挙動
  - OpenAI 呼び出し失敗やパース失敗時に例外を上位へ投げず、警告ログを残して安全なデフォルト（0.0 や空スコア）を使用する。これにより外部 API の一時障害が全処理停止を引き起こさないようにしている。

### Security
- 特になし（初期リリース）

### Notes / 補足
- DuckDB を主たるデータ格納／クエリ実行基盤として想定しており、関数は duckdb.DuckDBPyConnection を引数に取る設計。
- 日付処理はすべて date / naive datetime で扱い、タイムゾーン混入を避ける方針（JST→UTC の変換ロジックはコメントで明記）。
- 外部 API キー（OpenAI）は関数引数で注入可能。テスト時に環境変数依存を回避しやすい設計。
- 一部内部ユーティリティ関数（.env パーサ、OpenAI 呼び出しラッパ、JSON レスポンス復元ロジック等）はエッジケース（引用符、エスケープ、前後余計テキスト混入）に対応。

---

今後の予定（想定）
- strategy / execution / monitoring の実装拡充（現状はモジュール構成を公開）。
- 品質チェック（quality モジュール）との結合、ETL の運用ログ・監査出力強化。
- 追加のファクター・メトリクス・バックテストツールの追加。

（注）本 CHANGELOG は提供されたコードのドキュメント・実装コメントから推測して作成しています。必要であれば、実際のコミット履歴や差分に基づいたより詳細なエントリへ更新します。