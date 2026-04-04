# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

## [Unreleased]
（今後の変更をここに記載します）

## [0.1.0] - 2026-04-04
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開インターフェースに data, research, ai, などのサブパッケージを用意。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env / .env.local の読み込み優先順位を実装（OS環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env 行パーサーを実装し、以下に対応:
    - コメント行、先頭 export キーワード、シングル/ダブルクォート内のエスケープ、インラインコメント処理。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定などのプロパティを環境変数から取得可能に。
  - 環境変数検証機能を実装（KABUSYS_ENV, LOG_LEVEL の値チェック）。必須値未設定時は明示的な ValueError を送出。

- データ（kabusys.data）
  - ETL パイプライン結果の表現 ETLResult（dataclass）を追加。品質問題・エラーメッセージを集約して to_dict() で出力可能。
  - pipeline モジュールの骨組み（差分取得、保存、品質チェック方針を反映）。
  - calendar_management モジュールを追加:
    - JPX マーケットカレンダーの取り扱い（market_calendar）と夜間更新ジョブ calendar_update_job を実装。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録を優先し、未登録日の場合は曜日ベースでフォールバックする一貫したロジック。
    - バックフィル（過去数日再フェッチ）・健全性チェック（将来日付の異常検出）を実装。

- 研究用ユーティリティ（kabusys.research）
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）などを計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: PER、ROE を raw_financials と prices_daily から算出。
    - DuckDB を用いた SQL + Python 実装で、外部発注／API 呼び出しを行わない設計。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定ホライズンの将来リターン（fwd_1d, fwd_5d, fwd_21d 等）を計算。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関（IC）を計算（データ不足時は None）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
    - rank: 同順位は平均ランクで処理するランク化ユーティリティ。
  - research パッケージのトップレベルで主要関数を再エクスポート。

- AI / NLP（kabusys.ai）
  - news_nlp モジュール（score_news）を追加:
    - raw_news と news_symbols を集約し、銘柄ごとに複数記事を結合して OpenAI（gpt-4o-mini）に送信してセンチメントスコアを取得。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と calc_news_window を提供。
    - バッチ処理（最大 20 銘柄）、記事数/文字数トリム、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）と指数バックオフを実装。部分失敗時にも他コードの既存スコアを保護するため、書き込みは該当コードのみ DELETE → INSERT を実行。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector モジュール（score_regime）を追加:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・書き込み。
    - マクロニュース抽出（キーワードマッチ）、OpenAI 呼び出し、リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）、冪等な DB 書き込みを実装。
    - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を参照せず、target_date 引数を必須とする設計。

### Changed
- 設計面の方針記述を多数追加（コード内 docstring）：ルックアヘッドバイアス対策、DB 書き込みの冪等性、部分失敗時の保護、DuckDB の制約対応などを明示。
- OpenAI 呼び出し周りは JSON Mode を前提にし、レスポンスパースの堅牢化（前後に余計なテキストが混入するケースを部分抽出して復元）を行う。

### Fixed / Robustness
- DuckDB の executemany で空リストが不可な点に対するガード（params が空でないことをチェックしてから executemany を実行）。
- .env パーサーの強化により、クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの誤解析を防止。
- OpenAI API エラー処理を詳細化:
  - RateLimitError / APIConnectionError / APITimeoutError はリトライ対象。
  - APIError は status_code を安全に取得して 5xx の場合のみ再試行を試み、それ以外はフォールバック。
  - JSON パース/キー欠落時は例外を上げずフェールセーフにフォールバック（0.0／空辞書）して処理を継続。
- calendar_update_job における健全性チェック（将来の極端に大きい最終日を検出してスキップ）を追加。

### Security
- OpenAI キーや各種必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定の場合は ValueError を送出し明示的に失敗させることで、意図しない動作を防止。

### Notes / Implementation details
- すべての日付ロジックは naive date/datetime を使用し、タイムゾーン混入を避ける設計（ニュース窓は JST 指定を UTC に変換して使用）。
- DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等化。例外発生時は ROLLBACK を試行し、失敗ログを記録して上位に例外を伝播。
- テスト容易性に配慮し、外部 API 呼び出しを抽象化（内部 _call_openai_api は patch 可能）、Settings 等の環境依存を注入可能にする設計を採用。

---

今後のリリースでは以下が想定されます（未実装・改善案）:
- ai モジュールのモデル切替 / パラメータ化（モデル名やバッチサイズなどの設定化）
- score の時系列保存・履歴管理 UI / CLI
- 監視（monitoring）サブパッケージの実装（現状は設定項目のみ）
- より詳細な品質チェックプラグイン群の追加

貢献・バグ報告はリポジトリの issue をご利用ください。