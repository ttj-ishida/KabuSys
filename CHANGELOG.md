# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（kabusys）から推測して作成した初期リリース向けの変更履歴です。

なお日付はコード解析時点の暫定日付です（2026-03-29）。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - エクスポート対象モジュール: data, strategy, execution, monitoring。
- 設定管理
  - .env ファイルおよび環境変数から設定を読み込む自前のローダを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存しない読み込み。
    - .env のパース機能を充実（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数の保護（既存 OS 環境変数を上書きしない・上書き禁止キーの取り扱い）。
  - Settings クラス（settings インスタンス）を提供。必須値チェック（_require）と値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）を実装。
  - 各種設定プロパティを実装: J-Quants / kabuステーション / Slack / DB パス等。
- AI（Natural Language）機能
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）とそれに基づく記事抽出 calc_news_window を提供。
    - チャンクサイズ、文字数・記事数トリム、JSON Mode を用いた厳格なレスポンスバリデーションを実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。API失敗時はスキップして処理継続（フェイルセーフ）。
    - DuckDB 0.10 の制約を考慮した操作（executemany に空リストを渡さないなど）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ/バックオフ、API失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）により重複防止。
    - ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計。
  - AI モジュールの公開関数: score_news, score_regime。
- Data（ETL / カレンダー / パイプライン）
  - ETL インターフェースおよび結果型（ETLResult dataclass, src/kabusys/data/pipeline.py、src/kabusys/data/etl.py で再エクスポート）。
    - ETL の取得数・保存数・品質問題・エラー収集を表現。has_errors / has_quality_errors のプロパティを提供。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日の判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先・未登録日は曜日ベースのフォールバック。探索範囲の上限設定と健全性チェックを実装。
    - 夜間バッチ更新ジョブ（calendar_update_job）: J-Quants から差分取得して冪等保存（fetch/save 経路を jquants_client に委譲）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新、バックフィル、品質チェックとの統合を想定した設計。外部 jquants_client、quality モジュールと連携する設計。
- Research（ファクター／特徴量解析）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）、Liquidity（20 日平均売買代金、出来高比）などの計算を提供。
    - DuckDB SQL を多用した高効率実装。データ不足時の None の扱い等を明確化。
    - Z スコア正規化は kabusys.data.stats から提供する想定。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンのリターンを一括クエリで取得。
    - IC（Information Coefficient）計算（Spearman の ρ）: rank 関数を含む実装（同順位は平均ランク処理）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を実装。
- 内部実装上の設計方針・互換性配慮（ドキュメント・コードに明示）
  - ルックアヘッドバイアス防止（datetime.today()/date.today() を参照しない箇所の明示）。
  - 外部ライブラリへの依存を抑え、標準ライブラリ中心で実装（Research の一部は pandas 等に依存しない）。
  - DuckDB（SQL）を中心に設計。DuckDB のバージョン差分に配慮した実装注意点をコード内に記載（例: executemany の空リスト問題）。
  - OpenAI 呼び出しはテスト容易性のため差し替え可能（モジュール内 _call_openai_api を unittest.mock.patch でモック可能）。
  - LLM レスポンスの堅牢なパース（JSON mode における前後余分テキストの復元やエラーハンドリング）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト向け）かつ環境変数 OPENAI_API_KEY を参照する設計。必須未設定時は ValueError を投げることで誤動作を防止。

---

注意:
- 上記は現行ソースコードの実装内容・設計意図から推測して作成した CHANGELOG です。実際のリリースノートやバージョン管理履歴（コミットメッセージ等）が存在する場合は、それらに基づいて修正・補完してください。必要であれば、各モジュールごとのより詳細な変更点（関数単位の説明や既知の制約・TODO）も追加できます。