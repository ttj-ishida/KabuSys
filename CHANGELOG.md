CHANGELOG
=========

すべての重要な変更点を記録します。これは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, etc.）ごとに整理しています。
- 日付はリリース日を表します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ: kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ にて公開）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env のパースは export 形式・クォート・エスケープ・行末コメント等を考慮した堅牢な実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視/システム設定等のプロパティを公開。
  - 必須変数未設定時は明示的なエラーを送出（_require）。
  - 環境変数の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) にバッチ送信して ai_scores を書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数文字数上限、レスポンス検証（JSON モード + パース回復ロジック）を実装。
    - リトライ(指数バックオフ)とフェイルセーフ：429/ネットワーク断/タイムアウト/5xx をリトライ、その他はスキップして継続。
    - DuckDB への idempotent な書き込み（DELETE→INSERT。部分失敗時に既存データを保護）を実装。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily と raw_news を参照し、market_regime テーブルへ冪等書き込みを実装（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しのエラー処理・リトライ、パース失敗時のフォールバック（macro_sentiment=0.0）を備える。
    - ルックアヘッドバイアスを避ける設計（date 比較は排他条件、datetime.today() を直接参照しない）。
    - テストで差し替えられる内部 API 呼び出しポイントを用意。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日MA乖離）を計算する calc_momentum を実装。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - バリュー: 最新の raw_financials（report_date <= target_date）を用いて PER（EPS が有効な場合）と ROE を計算する calc_value を実装。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials のみ参照。
    - 結果は (date, code) をキーとした dict のリストで返却。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意 horizon のサポート、horizons の検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めで ties 検出の安定化）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - pandas 等の外部依存を使わず標準ライブラリと DuckDB で完結する実装。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を元に営業日判定・次/前営業日・期間内営業日リスト・SQ判定を提供。
    - DB 登録がない日や NULL 値は曜日ベースでフォールバックする一貫したロジックを採用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新。バックフィルと健全性チェック（未来日付の異常検知）を実装。
    - 最大探索日数制限を設けて無限ループを防止。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（etl モジュールで再エクスポート）。
    - 差分更新・保存・品質チェックのための設計方針とユーティリティを実装（jquants_client / quality との連携前提）。
    - DB テーブルの最大日付取得、テーブル存在チェック等のユーティリティ関数を実装。
    - 品質チェック結果を収集して ETLResult に含める仕組みを定義（Fail-Fast ではなく呼び出し元が判断）。

Other noteworthy implementation details
- DuckDB を主なローカルデータベースとして想定（DuckDB 接続型注入）。
- OpenAI の利用は gpt-4o-mini を想定し、JSON mode を使った精密なレスポンス取得と検証を実装。
- API 呼び出しの堅牢性強化 (再試行・指数バックオフ・5xx の取り扱い・非致命的失敗時のフォールバック)。
- データベース書き込みは冪等性を重視（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の明示管理）。
- ルックアヘッドバイアス防止: 全ての日付処理は target_date 引数を用い、内部で date.today()/datetime.today() を参照しない方針。
- テスト容易性: OpenAI 呼び出しなどを差し替え可能に実装（モック注入・patch 用ポイントを用意）。
- 外部依存の最小化: pandas 等に依存せず、標準ライブラリ + DuckDB + openai SDK で実装。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- OpenAI API キー等の機密情報は環境変数（OPENAI_API_KEY など）で管理することを前提とし、未設定時は ValueError を送出して明示的に失敗させる設計。

Notes / Future
- monitoring / execution / strategy パッケージは __all__ に含まれているが、今回のスナップショットでは各モジュールの実装（ファイル）が一部未展開の可能性あり。今後のリリースで発注・監視・ストラテジーの具体的な実装を追加予定。
- jquants_client, quality など外部連携モジュールとの統合テストを推奨。
- DuckDB バインドの挙動（executemany の空リストなど）に関する互換性注意点をコード内で扱っているため、運用環境の DuckDB バージョン確認を推奨。

---