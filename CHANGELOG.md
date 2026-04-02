CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

[Unreleased]
-------------

v0.1.0 - 2026-04-02
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージルート: kabusys（__version__ = 0.1.0）
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサは以下に対応:
    - "export KEY=val" 形式
    - シングル／ダブルクォート（エスケープ処理を考慮）
    - インラインコメント扱いのルール（クォート有無による）
  - Settings クラスを提供（J-Quants トークン、kabu ステーション、Slack、DB パス、監視閾値、環境／ログレベル等）。
  - 必須環境変数未設定時は明瞭な ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う（ルックアヘッド防止）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、その他はスキップして継続（フェイルセーフ）。
    - DuckDB の ai_scores テーブルへ冪等書き込み（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため api_key を引数で注入可能。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp の calc_news_window を利用して集約、OpenAI を利用して JSON 応答から macro_sentiment を取得。
    - API 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - DuckDB の market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT により）。
    - テスト用に OpenAI API 呼び出し箇所を差し替え可能。
- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった API。
    - market_calendar が未取得の場合は曜日ベース（平日）でフォールバックする堅牢な実装。
    - calendar_update_job により J-Quants API から差分取得 → 冪等保存（バックフィル・健全性チェック付き）。
  - pipeline:
    - ETLResult データクラスを公開（ETL の実行結果、品質問題・エラー集約を保持）。
    - ETL の設計方針に基づく差分更新・保存・品質チェックを想定（jquants_client / quality モジュールと連携する設計）。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。トゥルーレンジの NULL 伝播を明示的に扱う。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証あり。
    - calc_ic: スピアマンランク相関（IC）を計算。3 レコード未満は None を返す。
    - rank: 同順位は平均ランクを返す実装（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 研究系関数は DuckDB の prices_daily / raw_financials テーブルのみを参照する方針（本番発注等へ影響しない）。
- テスト/設計上の配慮
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（target_date を引数で受ける）。
  - OpenAI 呼び出し・API キー解決の注入によりユニットテストで差し替えやすい構造を採用。
  - DuckDB の executemany の実装上の制約に配慮（空リストを渡さないチェック等）。
- エラーハンドリングとロギング
  - OpenAI の各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）をケース別に扱い、リトライやフォールバックを実装。
  - DB 書き込み時は BEGIN/COMMIT/ROLLBACK を利用し、ROLLBACK が失敗した場合のログ出力を追加。
  - 多くの箇所で詳細な logger.info/debug/warning/exception を記録。

Changed
- 初版のため変更履歴なし。

Fixed
- 初版のため修正履歴なし。

Deprecated
- 初版のため非推奨項目なし。

Removed
- 初版のため削除事項なし。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で扱う旨を明記。API キー未設定時は ValueError を送出して安全に失敗。

Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を前提としているため、将来のモデルや API 変更時にはパース/レスポンス部分の調整が必要。
- DuckDB バインディングやバージョン依存の SQL 動作（list バインドや executemany の挙動）に注意。コード中に互換性対策が含まれているが、環境差異がある場合は追加対応が必要。
- ETL の上流・下流（jquants_client、quality モジュールなど）は本 changelog の範囲外。実運用前にそれらの実装と統合テストが必要。
- Slack / kabu API / J-Quants 等の外部連携は設定依存。必須環境変数が未設定の場合は明示的にエラーとなる。

開発者向け補足
- テストを書く際は以下を利用可能:
  - OpenAI 呼び出し箇所をモック（kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch）。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でオフにできる。
- 主要な公開 API:
  - kabusys.config.settings
  - kabusys.ai.score_news, kabusys.ai.score_regime
  - kabusys.data.calendar_management.*（is_trading_day, next_trading_day, calendar_update_job 等）
  - kabusys.data.ETLResult
  - kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

以上。