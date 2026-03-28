CHANGELOG
=========

すべての注目すべき変更点はここに記録します。  
このファイルは「Keep a Changelog」フォーマットに従っています。

v0.1.0 - 2026-03-28
-------------------

Added
- パッケージの初期リリース。
- 基本情報
  - パッケージバージョンを 0.1.0 に設定。
  - パッケージ公開用 __all__ を定義（data, strategy, execution, monitoring）。
- 設定管理 (kabusys.config)
  - .env / .env.local からの自動環境変数読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装: export 形式、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - _load_env_file の override / protected オプションにより OS 環境変数の上書き防止を実装。
  - Settings クラスを導入し、必須環境変数取得（_require）・デフォルト値・バリデーション（KABUSYS_ENV, LOG_LEVEL）・ユーティリティプロパティ（is_live 等）を提供。
- データプラットフォーム (kabusys.data)
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを公開。取得数・保存数・品質問題・エラー等を集約。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）に対応する設計。
  - ETL インターフェース re-export (etl)。
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（カレンダー未取得時も動作）。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 冪等保存（fetch/save のエラーハンドリング・バックフィル・健全性チェック付き）。
- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント (news_nlp)
    - raw_news と news_symbols から銘柄ごとの記事集約を行い、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - チャンク毎（デフォルト最大 20 銘柄）でバッチ送信、1 銘柄あたりの記事数・文字数上限を導入（トークン肥大化対策）。
    - レスポンス検証ロジック（JSON パース、results 配列、code/score 検査、数値変換、±1.0 クリップ）を実装。
    - API 障害（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライを実装。失敗時はそのチャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性向上のため _call_openai_api を経由し unittest.mock.patch により差し替え可能。
    - DuckDB executemany の空リストへの制約を回避する安全処理（空時は実行しない）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とニュース NLP によるマクロセンチメント（重み 30%）を合成して日次で市場レジームを判定（bull / neutral / bear）。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出しの最大リトライ、エラー時は macro_sentiment=0.0 のフォールバック、JSON パース失敗の安全処理を実装。
    - LLM 呼び出しはモジュール間で独立した private 実装を採用（news_nlp と共有しない）。
- リサーチツール (kabusys.research)
  - factor_research
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いたファクター計算（モメンタム、ATR、流動性、PER, ROE 等）。
    - 欠損やデータ不足時の挙動（None を返す等）を明確化。
  - feature_exploration
    - calc_forward_returns（複数ホライズン対応・SQL 一括取得）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
  - data.stats からの zscore_normalize 再エクスポートを提供。
- ロギング・監視
  - 各モジュールで詳細な情報ログ・警告ログを追加し、失敗時の診断を容易に。

Fixed / Robustness
- OpenAI API 呼び出し部の堅牢化
  - RateLimitError・APIConnectionError・APITimeoutError・5xx に対するリトライ（指数バックオフ）を実装。
  - APIError の status_code の有無に依存しない安全な判定ロジックを導入。
  - JSON mode でも前後に余計なテキストが混ざるケースに対する復元ルーチン（最外の {} を抽出）を追加。
  - 全リトライ失敗やパース失敗時は例外を投げず 0.0（中立）や空結果でフォールバックする方針を採用（フェイルセーフ）。
- DuckDB 関連の安定性
  - executemany に空リストを渡すと失敗する DuckDB の挙動を回避するため、実行前に空チェックを行う。
  - SQL はパラメタライズされており、直接埋め込みを最小化（SQL インジェクションリスク低減）。
- トランザクション安全性
  - DB 書き込み時に BEGIN / DELETE / INSERT / COMMIT を使用し、例外時に ROLLBACK を行う。ROLLBACK に失敗した場合は警告ログ出力。
- .env パーサの堅牢化
  - 引用符付き値のエスケープ処理、コメント認識、export プレフィックス対応等の強化。
  - 読み込み失敗時は警告を出力して処理を続行。

Changed / Design decisions
- 全ての日時計算で datetime.today()/date.today() を直接参照しない設計を基本方針に採用（ルックアヘッドバイアス防止）。各処理は引数の target_date を基準に動作。
- LLM 呼び出しやデータ取得は「失敗しても全体を止めない（できるだけ部分的に継続）」というフェイルセーフ設計を採用。
- モジュール間の内部関数の共有を最小化（news_nlp と regime_detector で _call_openai_api を共有しない等）してモジュール結合度を下げ、テスト容易性を向上。

Removed / Deprecated
- なし（初期リリースのため該当なし）。

Security
- .env 読み込み時に既存の OS 環境変数をデフォルトで保護（protected set）。.env.local は override フラグで OS 環境変数を上書き可能だが、protected により上書きを避けることができる。

Notes / Known limitations
- AI モジュールは OpenAI API（gpt-4o-mini）に依存するため、API キー（OPENAI_API_KEY）が必要。api_key 引数で明示注入可能。
- ai/news_nlp の出力は LLM に依存するため、レスポンスフォーマットや品質はモデル挙動に左右される。レスポンス検証とクリッピングを入れて悪影響を軽減しているが、長期的には追加のモニタリングや監査が望ましい。
- DuckDB バージョンの差異（list バインドの挙動など）に配慮した実装を行ったが、環境差異での追加対応が必要になる可能性がある。

今後の予定（例）
- strategy / execution / monitoring の実装拡張（初期公開ではエクスポート対象だが実装は今後拡充）。
- AI モデル評価の自動化・モニタリング（レスポンス品質指標の追加）。
- ETL のスケジューリングや監査ログ出力の強化。

---

この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は、必要に応じて調整してください。