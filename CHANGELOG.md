CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

- リリース日付は YYYY-MM-DD 形式です。
- 重大な変更はカテゴリ別（Added / Changed / Fixed / Security / Internal）で記載します。

Unreleased
----------

（次回リリースに向けた未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリースを追加。
- パッケージ構成:
  - kabusys パッケージの公開 (data, strategy, execution, monitoring) を定義。
  - バージョン: 0.1.0
- 環境設定/ロード:
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
  - 読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - .env の読み込み時に OS 環境変数を保護する機能（protected set）を実装。
  - 高レベル Settings クラスを追加し、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定をプロパティで公開。
  - Settings に is_live / is_paper / is_dev 等のユーティリティプロパティを追加。
- AI (自然言語処理):
  - kabusys.ai.news_nlp モジュールを追加:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - バッチ処理（1回あたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数制限）、JSON レスポンスのバリデーションを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）とエクスポネンシャルバックオフを導入。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - kabusys.ai.regime_detector モジュールを追加:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事取得、LLM によるマクロセンチメント評価、スコア合成、閾値判定、DB トランザクション処理を実装。
- Research（リサーチ）:
  - kabusys.research パッケージを追加。
  - factor_research モジュール:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials に基づく定量ファクター）。
  - feature_exploration モジュール:
    - calc_forward_returns, calc_ic, factor_summary, rank を実装（将来リターン計算、IC、統計サマリー等）。
  - re-export: zscore_normalize（kabusys.data.stats から）。
- Data（データ処理）:
  - calendar_management モジュールを追加:
    - market_calendar に基づく営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 未登録日の曜日フォールバック、最大探索幅の制限、カレンダーの夜間更新 job（calendar_update_job）を実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - 差分取得 / 保存 / 品質チェックのための基盤を実装（jquants_client 経由の保存、バックフィル、品質問題の収集）。
- ロギング: 主要処理において情報・警告・デバッグログを充実。

Changed
- 時間参照の意思決定:
  - AI / ETL / Research モジュールは内部で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取ることでルックアヘッドバイアスを防止）。
- DB 書込みの冪等性確保:
  - market_regime / ai_scores 等への書き込みは「DELETE（該当コード）→ INSERT」またはトランザクション（BEGIN/COMMIT）で冪等性を担保。
  - 部分失敗時に既存データを保護する（書き込むコードを限定して削除）。
- OpenAI 呼び出しに関する挙動:
  - JSON Mode を前提にレスポンスを厳密に検証・修復（前後の余計なテキストが混入した場合は最外側の JSON オブジェクトを抽出してパース試行）。
  - 429 / ネットワーク / タイムアウト / 5xx の場合はリトライ、その他の APIError は安全にスキップして処理継続。
  - マクロスコア・ニューススコアともに API 失敗時はフェイルセーフで 0.0 を採用（例外を上げずに処理を継続）。
- DuckDB 互換性処理:
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 の制約に対応）。

Fixed
- .env パーサの強化 / 不具合修正:
  - export KEY=val 形式をサポート。
  - シングル/ダブルクォート内でのバックスラッシュエスケープに対応して正しく値を抽出。
  - クォート無し値において '#' がコメント開始かどうかを直前文字で判別するルールを実装（スペース/タブ直前ならコメントとして扱う）。
  - 空行・コメント行のスキップ処理を適切に行う。
- news_nlp レスポンス検証の堅牢化:
  - LLM が整数で code を返す場合に備えて文字列に正規化して照合。
  - スコアが数値でない場合や非有限値の場合は無視しログ出力。
- トランザクション失敗時の安全なロールバック:
  - DB 書き込み時に例外発生 → ROLLBACK 試行、ROLLBACK 自体が失敗した場合は警告ログを出す実装。
- calendar_management の挙動:
  - market_calendar テーブルが存在しない／空の場合は曜日ベースのフォールバックを一貫して適用するよう修正。
  - next/prev_trading_day の最大探索日数超過時に明確な ValueError を送出するようにした。

Security
- API キー必須チェック:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合に ValueError を送出。
- 自動 .env ロードの明示的無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加し、テスト環境等での意図しない環境変数変更を防止。
- OS 環境変数を protected として .env からの上書きを防止する仕組みを導入。

Internal
- テスト補助:
  - OpenAI 呼び出し関数（各モジュールの _call_openai_api）を patch 可能にしてユニットテストで差し替えやすくした。
- 設計・実装ノートを各モジュールに追加（ルックアヘッドバイアス防止、フェイルセーフ方針、DuckDB 互換性等）。
- ロガー名や警告文を明確化して運用時のトラブルシュートを容易に。

Notes / Known limitations
- 現時点では PBR や配当利回りなど一部バリューファクターは未実装（calc_value に注記あり）。
- ai モジュールは OpenAI の JSON Mode 出力に依存するため、将来的なモデル・API 仕様変更に応じた保守が必要。
- ETL / pipeline の上位入口（スケジューラや CLI）は本リリースに含まれていない可能性がある（コアライブラリとしての提供にフォーカス）。

作者: kabusys 開発チーム
---