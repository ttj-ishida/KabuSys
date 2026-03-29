# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、ソースコードから推測される機能追加・設計方針・既知の注意点をもとに作成された初回のリリースノートです。

全般:
- 日付はリリース日を示します。
- バージョンはパッケージの __version__ に合わせています（src/kabusys/__init__.py: 0.1.0）。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初回リリース — 日本株自動売買システムのコアライブラリを公開。

注: 以下の記載はコードベースから推測してまとめた機能説明・設計上の注意点です。

Added
- パッケージ構成（kabusys）
  - サブパッケージを公開: data, research, ai, monitoring, strategy, execution（__all__ 指定）
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml）
  - export KEY=val 形式やクォート・エスケープ、インラインコメントの取り扱いに対応する独自パーサを実装
  - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - 必須キー取得 helper (_require) と Settings クラスで以下をプロパティ提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL の検証
    - is_live / is_paper / is_dev 判定ショートカット
- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメントを取得
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事数・文字数トリムを実装
    - リトライ（429/ネットワーク/タイムアウト/5xx は指数バックオフ）およびレスポンスの堅牢なバリデーション
    - 成果物を ai_scores テーブルへ冪等的に書き戻す（DELETE → INSERT、部分書込による保護）
    - 時刻ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime）
    - テスト容易性のため _call_openai_api の差し替えを想定
  - regime_detector.score_regime:
    - ETF (1321) の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定
    - マクロ記事抽出はニュースモジュール calc_news_window を利用、最大20記事、OpenAI で JSON レスポンスを期待
    - フェイルセーフ設計: API 失敗時は macro_sentiment=0.0 として継続
    - market_regime テーブルへ冪等書込（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理
    - テスト用に _call_openai_api の差し替えを想定
  - OpenAI クライアントは openai.OpenAI を使用し、モデルは gpt-4o-mini を指定
- データ関連（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - market_calendar がない場合の曜日ベースフォールバック（土日を休場扱い）
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した判定を行う設計
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新、バックフィル／健全性チェックを実装
  - pipeline / ETL:
    - ETLResult データクラス（ターゲット日・取得数/保存数・品質問題・エラー集計等）
    - 差分更新ロジック、バックフィル、品質チェック（quality モジュールとの連携）を想定
    - _get_max_date 等の DB ヘルパー実装
- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算（欠損やデータ不足時の None 処理）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算
    - 全関数は DuckDB と prices_daily / raw_financials を参照する設計（外部 APIにアクセスしない）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）について将来リターンを計算（引数の検証あり）
    - calc_ic: スピアマンランク相関（IC）を計算（ペアが 3 件未満なら None）
    - rank: 同順位は平均ランクで処理（浮動小数丸めで ties を安定化）
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出（None 除外）
- その他
  - duckdb を主要なローカルデータストアとして利用する設計を反映
  - ロギング（logger）を各モジュールで活用し、情報・警告・例外時のログ出力を整備
  - テストフレンドリーな設計: ネットワーク外部呼び出し部分をモック差し替えしやすい作り（内部の _call_openai_api など）

Changed
- 初回リリースのため該当なし（新規実装中心）

Fixed
- 初回リリースのため該当なし

Security
- センシティブ情報は環境変数（OPENAI_API_KEY 等）で管理する設計
- .env 自動読み込み時に OS 環境変数を保護する仕組みを導入（protected set）
- 注意: 実行環境で必要な環境変数が未設定の場合、Settings のプロパティで ValueError を送出する（明示的な失敗）

Breaking Changes
- 初回リリースのため該当なし

Notes / Known issues / 使用上の注意
- OpenAI API キー（OPENAI_API_KEY）を必須とする機能（news_nlp.score_news、regime_detector.score_regime）
- J-Quants API 関連のクライアント（kabusys.data.jquants_client）は別モジュールとして利用想定（本リポジトリ内で参照はあるが実装はここに含まれない場合がある）
- DuckDB の executemany に関する互換性を考慮した実装上の注意がある（空パラメータの扱い回避）
- 時刻処理は内部的に UTC naive datetime を使用しており、ウィンドウ計算は JST をベースに UTC へ変換している（タイムゾーンの扱いに注意）
- ルックアヘッドバイアス対策のため、全ての関数は内部で datetime.today()/date.today() の直接参照を避け、caller が target_date を渡す設計
- API 呼び出しは再試行ロジックを持つが、最終的にフォールバック（0.0 やスキップ）して処理を継続するため、外部依存の一時障害に対してフェイルセーフであることを意図している

参考（実装上の重要ポイント）
- OpenAI 呼び出し: gpt-4o-mini、response_format={"type": "json_object"} を利用
- ニュースウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST → UTC に変換して DB クエリで扱う
- レジーム判定: ETF 1321 の ma200 乖離に 0.7 の重み、マクロセンチメントに 0.3 の重みを与え、閾値で bull/bear/neutral を判定
- DB 書き込みは基本的に BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用、例外時に ROLLBACK を試みる

---

この CHANGELOG はコードからの推測に基づいて作成しています。実際のリリースノートとして公開する際は、著者・貢献者情報、コミットハッシュ、外部依存バージョン（duckdb / openai など）や導入手順を追記することを推奨します。