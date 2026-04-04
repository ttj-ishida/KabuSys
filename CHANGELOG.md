# CHANGELOG

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

- リリース日付はコミット/パッケージ作成時に記載しています。
- ここに記載されている内容はソースコードから推測してまとめた機能・設計上の変更点・注意事項です。

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added
- 基盤パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージ初期化: src/kabusys/__init__.py（公開モジュール一覧とバージョン管理）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - .env パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープを考慮）。
  - OS 環境変数を保護する protected オプションと、override の挙動制御。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 必須環境変数未設定時に ValueError を送出する _require ユーティリティ。
  - アプリケーション設定をまとめた Settings クラス（J-Quants、kabu API、LINE、DB パス、監視閾値、環境/ログレベル判定など）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の有効値チェック）。
- AI 関連
  - ニュースセンチメント分析（src/kabusys/ai/news_nlp.py）
    - 指定タイムウィンドウ（JST 前日 15:00 〜 当日 08:30）に基づく記事集約ロジック。
    - 銘柄ごとに最大記事数・文字数でトリムして OpenAI (gpt-4o-mini) にバッチ送信（最大バッチサイズ: 20 銘柄）。
    - JSON Mode を想定したレスポンスバリデーション、JSON パース復元処理（前後ノイズの補正）、スコアクリップ（±1.0）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を用いたエクスポネンシャルバックオフ。
    - DuckDB 互換性考慮（executemany に空リストを渡さない、DELETE→INSERT の idempotent な置換戦略）。
    - 単体テスト用フック: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出ロジック（マクロキーワードベース）、OpenAI 呼び出し（gpt-4o-mini）によるスコア化、リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジームスコア合成と閾値判定、market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - lookahead バイアス回避設計（datetime.today() などを参照しない、DB クエリは target_date 未満を参照）。
- データ関連
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照した営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録データを優先し、未登録日は曜日ベース（週末判定）でフォールバックする一貫したロジック。
    - 最大探索日数制限により無限ループを防止。
    - JPX カレンダー夜間更新ジョブ（calendar_update_job）実装。J-Quants クライアント経由で差分取得し冪等保存。バックフィルおよび健全性チェックを実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 実行結果を表す ETLResult データクラスを公開（to_dict による品質問題のシリアライズ機能含む）。
    - 差分取得・バックフィル方針、品質チェックの収集方式（Fail-Fast ではなく問題を収集して上位で判断）など設計方針を実装。
    - DuckDB テーブル存在チェック・最大日付取得等のユーティリティ実装（ETL の下支え）。
  - データアクセスの公開インターフェース（kabusys.data.etl で ETLResult を再エクスポート）。
- 研究（Research）モジュール（src/kabusys/research/*.py）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M）、200 日 MA 乖離、ATR ベースのボラティリティ・流動性指標、財務ベースのバリュー（PER, ROE）の計算。
    - DuckDB 上で完結する SQL + Python 実装、データ不足時は None を返す安全な設計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（任意ホライズン、ホライズン検証、単一クエリでの取得）。
    - IC（Spearman のランク相関）計算、rank ユーティリティ（同順位は平均ランク）、factor_summary による統計要約。
  - 研究用ユーティリティを __init__ で再エクスポートして公開。
- ドキュメント的な設計注釈を多数コード内コメントとして追加（lookahead バイアス対策、DuckDB 互換性、フェイルセーフの方針等）。

### Changed
- （初版）API 呼び出しの仕様上の注意点やバリデーション・フェイルオーバーの設計をコード内で明文化。  
  例: OpenAI 未設定時は明示的に ValueError を投げる、API エラーの扱い（5xx リトライ、その他はスキップ）など。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行末コメント処理（クォートあり/なしの違い）に対応。
  - 空行・コメント行を無視する処理を実装。
- DuckDB 実行に関する互換性対応:
  - executemany に空リストを渡さない（DuckDB 0.10 の制約への対応）。
  - list 型バインドの不安定性回避のため DELETE を個別に実行してから INSERT する方式を採用。

### Security
- 環境変数の自動読み込み時、既存の OS 環境変数を protected として上書きから保護する仕組みを導入（重要なトークンや資格情報が .env によって意図せず上書きされるのを防止）。

### Notes / Implementation Decisions
- AI モジュール（news_nlp, regime_detector）はいずれも以下を遵守:
  - ルックアヘッドバイアスを避けるため datetime.today() や date.today() を内部で参照しない（必ず target_date を外部から与える）。
  - OpenAI 呼び出しはテスト容易性のため差し替え可能な内部フックを提供。
  - API 失敗時は全体を停止させず、局所的にフェイルセーフ（スコア 0.0、該当銘柄スキップ等）で処理を継続する方針。
- DuckDB をデータレイヤーに採用したことを前提に、互換性と実運用上の注意（空リストバインドや日付型処理）をコード内で扱っている。

---

（注）上記 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のコミット履歴・リリースノートと差分がある場合は、差分を反映して更新してください。