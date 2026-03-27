CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。  
このファイルはコードベースから推測できる機能追加・設計方針・品質改善点を要約しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタデータ: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、CWD に依存しない自動ロードを実現。
  - .env のパース機能を強化（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメント取り扱いの差別化）。
  - 上書き制御（override）と OS 環境変数保護（protected set）を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。以下の環境変数を参照するプロパティを持つ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト開発用 URL を提供）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（値検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
- AI 関連モジュール（src/kabusys/ai/）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON Mode で問い合わせて銘柄別センチメントを取得。
    - タイムウィンドウ計算関数 calc_news_window（JST を基準に UTC で返す）を提供。
    - バッチ処理（1 API コールあたり最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの記事・文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ）と失敗時フォールバック（スキップ）。
    - レスポンスの堅牢なバリデーション（JSON パース、"results" 構造、コード照合、数値検証）とスコアの ±1.0 クリップ。
    - DuckDB への書き込みは部分更新戦略（該当コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
    - テスト用に _call_openai_api を patch 可能に設計。
  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタで raw_news を抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを JSON 出力で取得。
    - API 呼び出しのリトライ（最大回数・指数バックオフ）、API 障害時は macro_sentiment = 0.0 にフォールバック。
    - ma200_ratio の算出はデータ不足時に中立値 (1.0) を返す安全策を導入。
    - 計算結果は market_regime テーブルに冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - look-ahead バイアス防止のため、date の判定に datetime.today()/date.today() を使用しない設計（入力の target_date を厳密に使用）。
- 研究（Research）モジュール（src/kabusys/research/）
  - factor_research.py
    - Momentum（1M/3M/6M リターン, 200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金, 出来高比）を DuckDB 上で計算。
    - データ不足時の None 返却やスキャン期間バッファの設計を実装。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応、ホライズン validation）、IC（Spearman ランク相関）calc_ic、ランク関数 rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存を避け、標準ライブラリのみで統計処理を実装。
  - research パッケージ初期公開インターフェースを整備（__init__.py）。
- データ（Data）モジュール（src/kabusys/data/）
  - calendar_management.py
    - JPX マーケットカレンダーを扱うユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日を休日として扱う）。
    - 夜間バッチ更新 calendar_update_job を実装し、J-Quants クライアントから差分取得して冪等に保存。バックフィルや健全性チェックを組み込み。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新・保存・品質チェックの設計に基づく ETLResult データクラスを提供（target_date, fetched/saved counts, quality_issues, errors を含む）。
    - DuckDB のテーブル最大日付取得・テーブル存在チェックなどのユーティリティを実装。
    - 市場カレンダー補正や最終取得日からの差分算出ロジック（バックフィル考慮）を実装。
  - etl.py で ETLResult を再エクスポート。
  - data パッケージの公開インターフェースを整備（__init__.py）。
- その他
  - jquants_client など外部クライアントと連携する設計を想定（calendar, ETL, データ保存に利用）。
  - ロギングを各モジュールに導入し、情報・警告・例外ログを適切に出力する設計。

Changed
- 初期リリースにつき変更履歴はなし。

Fixed
- 初期リリースにつき修正履歴はなし。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の取り扱いおよび自動ロードにおいて、OS 環境変数を上書きしない保護機構（protected set）を実装。  
- 必須 API キーが未設定の場合は明示的に ValueError を出して早期に失敗させる設計（OpenAI API キー、Slack、Kabu API、J-Quants リフレッシュトークン等）。

注記（設計上の重要点）
- ルックアヘッドバイアス防止: AI スコアリング・レジーム判定・リサーチ関数は date.today()/datetime.today() に依存せず、呼び出し側から与えられた target_date を厳密に使用するように設計されています。
- OpenAI 呼び出し: JSON Mode を利用した厳格な JSON 出力を期待しつつ、レスポンス混入テキスト（前後の余計な文字）への耐性を持つパースロジックを備えています。
- DuckDB 互換性: executemany に空リストを渡さない等、DuckDB のバージョン依存問題へ配慮した実装が行われています。
- フェイルセーフ: 外部 API エラーは可能な限り局所で処理（ログ出力・フォールバック）し、システム全体の停止を避ける設計方針が反映されています。

今後の予定（推測）
- J-Quants / kabu ステーションとの実際の統合テスト、監視・運用用モジュール（execution / monitoring）の実装拡充、学習済みモデルや特徴量のチューニング、テストカバレッジ強化が想定されます。