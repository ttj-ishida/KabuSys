CHANGELOG
=========

すべての変更は Keep a Changelog に準拠し、セマンティックバージョニングを採用します。
このファイルはコードベースから推測できる機能追加・設計方針・重要な実装ポイントを
まとめた初期リリース向けの変更履歴です。

0.1.0 - 2026-03-31
-----------------

Added
- 基本パッケージ
  - パッケージ名 kabusys を導入。パッケージバージョンを __version__ = "0.1.0" として公開。
  - public API として data, strategy, execution, monitoring を __all__ で公開（モジュール群のエントリポイントを整備）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local ファイルおよび環境変数から設定値を自動的に読み込む仕組みを実装。
    - 読み込み順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途向け）。
    - プロジェクトルート検出は __file__ を基準に .git または pyproject.toml を探索（配布後の動作を考慮）。
  - .env パーサで以下に対応:
    - コメント行や空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしのインラインコメント処理（直前が空白/タブの '#' をコメントと認識）
  - Settings クラスを導入してアプリケーション設定をプロパティ経由で提供:
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境種別・ログレベル等を取得可能
    - 必須環境変数未設定時は明確な ValueError を送出（_require）
    - デフォルト値（例: KABUSYS_ENV=development, LOG_LEVEL=INFO, データベースファイルパスなど）を定義
    - env/log_level の値検証（許容値外は ValueError）

- AI（NLP）関連 (kabusys.ai)
  - ニュースセンチメント分析モジュール (news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成、OpenAI（gpt-4o-mini）の JSON mode を用いて一括評価。
    - チャンク処理（1 API 呼び出しあたり最大20銘柄）と 1 銘柄あたりのトークン制限（記事数および文字数のトリム）を実装。
    - 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスに対する厳格なバリデーション（JSON 抽出、results 配列、code/score 型検証、未知コード無視、数値チェック）。
    - スコアは ±1.0 にクリップし、成功分のみ ai_scores テーブルへ置換的に書き込み（DELETE→INSERT を採用して部分失敗時の保護）。
    - テスト容易性のため _call_openai_api をパッチで差し替え可能に実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算（ルックアヘッド防止）。
  - 市場レジーム判定モジュール (regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース由来の LLM センチメント（重み 30%）を合成して日次レジームを判定（bull/neutral/bear）。
    - OpenAI 呼び出しは独立実装とし、記事なし、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - リトライ（429/接続/タイムアウト/5xx）や JSON パース失敗に対するフェイルセーフ実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データ基盤 / ETL (kabusys.data)
  - ETLResult データクラスと pipeline 用インターフェースを追加（ETL 結果構造の統一）。
  - カレンダー管理 (calendar_management)
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装: J-Quants から差分取得し market_calendar に idempotent に保存。
    - バックフィル（直近 _BACKFILL_DAYS 日分を再取得）や異常検知（未来日が極端に遠い場合はスキップ）を実装。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。market_calendar が未取得の場合は曜日ベースのフォールバック（週末除外）。
    - 最大探索日数を定義して無限ループを防止（_MAX_SEARCH_DAYS）。
  - ETL パイプライン基盤 (pipeline)
    - 差分更新、保存（jquants_client の save_* を想定）および品質チェックの設計を反映した基盤的実装（ETLResult 等）。
    - デフォルトのバックフィルや品質チェックの扱い（重大度を収集し呼び出し元に委ねる）をサポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR／相対 ATR）、Value（PER/ROE）、Liquidity（20 日平均売買代金・出来高比率）を計算する関数を実装。
    - DuckDB SQL ウィンドウ関数を活用して営業日・連続レコードベースで計算。データ不足時は None を返す設計。
    - 設計として外部 API にはアクセスせず prices_daily / raw_financials のみ参照。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns、デフォルト horizons=[1,5,21]）、IC（Information Coefficient）計算（Spearman のランク相関）、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装（テスト容易性・依存軽量化）。
    - 欠損値・有限性チェックを厳格に行い、必要最小単位で None を返す方針。

Changed
- （初期リリースのため「追加」が中心。設計上の方針やデフォルト値をコードコメント・実装として反映）
  - ルックアヘッドバイアス対策: 各モジュール（news_nlp, regime_detector, research 等）は内部で datetime.today()/date.today() を直接参照しない設計（外部から target_date を注入する API を採用）。

Fixed
- （実装中に想定される堅牢性改善を明示）
  - DuckDB executemany の空リスト制約に対する対策: executemany 呼び出し前に空チェックを行い互換性を確保（ai_scores 書き込み等）。
  - DB 書き込み時のトランザクション保護: 例外発生時に ROLLBACK を試み、さらに ROLLBACK に失敗した場合は警告ログを出力。

Security
- 環境変数の取り扱いに注意:
  - 必須トークン（OpenAI / J-Quants / Slack 等）は _require による明示エラーで検出。
  - .env 自動ロード時に既存 OS 環境変数を保護する protected セットを導入（.env.local で上書き可能だが OS 環境変数は既定で保護）。

Notes / Implementation details
- OpenAI 連携:
  - gpt-4o-mini を利用する前提の実装（JSON mode を使用）。API キーは引数で注入可能で、 None の場合は環境変数 OPENAI_API_KEY を参照する。
  - API 呼び出しの挙動をテストしやすくするため _call_openai_api をモジュールローカル関数に分離し、unittest.mock で差し替え可能。
  - API エラー時はフェイルセーフでスコアを 0.0 にフォールバックするか、該当チャンクをスキップする設計。

- DuckDB 前提:
  - 主要処理は DuckDB 接続を受け取り SQL と Python を組み合わせて行う（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを参照）。
  - 日付列の扱いに注意し、DuckDB からの値を date オブジェクトへ変換するユーティリティを用意。

- ロギング:
  - 処理状況・リトライ情報・パース失敗等を logger に詳細に出力する設計。運用時の監視に配慮。

Acknowledgements / TODO（今後の想定）
- execution / monitoring / strategy 等の公開 API は __all__ で示されているが、この変更履歴は現在提供されているモジュールに基づく内容で、実運用向けの発展（発注ロジック・監視エージェント等）は今後の開発項目として想定される。
- docs やマイグレーション手順、テストカバレッジ向上、CI/CD やパッケージ配布（wheel）に関する整備が今後の課題。

----- 

この CHANGELOG はコード内のコメント・実装から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース差分に基づいて適宜調整してください。