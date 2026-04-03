Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-03
-----------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。
- 環境設定・読み込み機能
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサの強化: export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理を正しく解釈。
    - OS 環境変数を保護する protected 上書き制御、override フラグ対応。
    - Settings クラスを公開 (J-Quants トークン、kabu API 設定、LINE トークン、DB パス、監視閾値、環境/ログレベル検証など)。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値セット確認）。
- データ基盤（DuckDB ベース）のユーティリティ
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass による ETL 実行結果の構造化（品質問題・エラーの集約、辞書変換機能を含む）。
    - 差分取得・バックフィル方針、品質チェックフローを想定した ETL 設計。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の公開エイリアス。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API。
    - calendar_update_job: J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック付き）。
    - カレンダーデータ未取得時の曜日ベースのフォールバックや最大探索日数制限などの保護ロジック。
    - DuckDB の日付値ハンドリングやテーブル存在チェック等のユーティリティ実装。
- 研究（リサーチ）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR(20)、流動性（平均売買代金・出来高比）などファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で完結する SQL ベースの実装。データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たない純標準ライブラリ実装、入力検証（horizons 上限など）。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- AI / NLP 機能（OpenAI 経由のスコアリング）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄別センチメント分析機能 (score_news)。
    - ニュース収集ウィンドウ計算（calc_news_window：前日15:00 JST〜当日08:30 JST を UTC な naive datetime で算出）。
    - 銘柄ごとに記事を集約し（最大件数・文字数でトリム）、最大 20 銘柄/チャンクで OpenAI API に送信するバッチ処理。
    - JSON Mode を想定したレスポンスの検証・パース（_validate_and_extract）。スコアを ±1.0 にクリップ。
    - 429/ネットワークエラー/タイムアウト/5xx に対する指数バックオフリトライ、API失敗時はスキップして処理継続（フェイルセーフ）。
    - DuckDB executemany の空リスト制約を考慮した安全な DELETE/INSERT ロジック（部分失敗時に既存スコアを保護）。
    - テスト時に差し替え可能な _call_openai_api フックを用意。
  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定 (score_regime)：ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - prices_daily からの MA 計算、raw_news からのマクロキーワードフィルタ、OpenAI 呼出し（gpt-4o-mini）によるマクロセンチメント評価を実装。
    - レジームスコアは clip(-1,1)、閾値を基にラベル付け。DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - API リトライ・エラー種別毎の扱い（5xx はリトライ、それ以外はフォールバック）、API失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - テスト用に OpenAI 呼び出しを差し替え可能な内部関数を用意。
- モジュール分割・エクスポート
  - ai, data, research パッケージの最小構成を提供。各モジュールで __all__ を整理して主要 API を公開。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス回避:
  - AI スコアリングとレジーム判定は関数引数の target_date を用い、datetime.today()/date.today() を直接参照しない設計。
  - DB クエリでは target_date 未満／前日基準などの排他条件を利用。
- フェイルセーフ:
  - OpenAI など外部 API の失敗時にはゼロやスキップで継続する（例外を上位に伝播させない箇所が多い）。
- テスト配慮:
  - OpenAI 呼び出し部分はモジュール毎に差し替え可能に実装（mock で置換しやすい）。
  - 環境読み込みの自動化は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB 互換性:
  - executemany に空リストを渡せない制約を考慮した実装や、型/日付扱いの安全化が行われている。
- DB 書き込みは冪等性を重視（DELETE→INSERT のパターン、ON CONFLICT を想定した保存ロジック等）。

今後の予定（想定）
- 監視（monitoring）や実行（execution）などの実際の発注・監視モジュールの実装拡張。
- テストカバレッジの追加、エンドツーエンドの統合テスト整備。
- J-Quants / Kabu API クライアント周りの追加実装とドキュメント整備。

---