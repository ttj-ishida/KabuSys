CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ宣言および公開 API を定義（src/kabusys/__init__.py）。
- 環境設定/自動ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（配布後の動作を考慮）。
  - .env パーサは export 文、クォート文字列、インラインコメント、バックスラッシュエスケープなどに対応。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスでアプリケーション設定を提供。型変換・既定値・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。
  - データベースパス、監視用ファイルパス、リソース閾値設定等を環境変数で制御可能。
- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
  - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）を実装（calc_news_window）。
  - バッチ処理（最大20銘柄/回）、記事トリム（最大記事数・文字数）を実装しトークン肥大化を抑制。
  - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
  - レスポンス検証ロジックを実装（JSON整形・results リストの検証・コード正規化・スコア数値化・±1.0 クリップ）。
  - 部分失敗に備え、取得成功した銘柄のみ ai_scores テーブルに置換的に書き込み（DELETE → INSERT）。
  - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計。
- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を評価。
  - マクロニュース抽出はキーワードベース、OpenAI 呼び出しは JSON モードで実行。API エラー時は macro_sentiment=0.0 としてフォールバック。
  - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用、datetime.today() を直接参照しない）。
  - 計算結果は idempotent に market_regime テーブルへ保存（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
- データ ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返却/ログに利用可能。
  - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
- カレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX カレンダー（market_calendar）の夜間差分更新ジョブ（calendar_update_job）を実装。
  - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
  - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
  - バックフィルや健全性チェック（極端に未来の日付を検出した場合はスキップ）を実装。
- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター群を提供: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials のみに依存）。
  - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応。入力検証あり（horizons は 1..252）。
  - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。データ不足時は None を返す。
  - ランク化ユーティリティ（rank）と統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
- データ接続/クエリ基盤
  - DuckDB を利用した SQL + Python ハイブリッド実装を採用（各関数は DuckDB 接続を受け取り DB 内のテーブルを参照）。
- パッケージモジュール再エクスポート
  - 主要ユーティリティ（kabusys.data.ETLResult 等）を公開エンドポイントとして再エクスポート。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）
  - ただし多くの関数でフェイルセーフやロールバック処理、API リトライなどの耐障害設計を導入済み。

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を投げることで誤用を防止。

Notes / 既知の設計および互換性について
- DuckDB の executemany に空リストを渡せない制約（DuckDB 0.10 等）に配慮して条件分岐を挿入している。
- datetime.today() や date.today() を直接参照しない設計を徹底し、ルックアヘッドバイアスを防止。
- OpenAI 呼び出しは JSON Mode を想定。レスポンスの前後ノイズや不正 JSON に対する復元処理を行う（外側の {} を抽出して再パース等）。
- API 呼び出し失敗時は「安全なデフォルト」（例: macro_sentiment=0.0、スコア未取得銘柄はスキップ）で継続する設計。
- .env パーサは多くの実用ケース（export 指定、クォート、コメント、エスケープ）に対応。ただし極端に複雑なシェル構文は想定外。
- market_calendar がまばらにしか存在しないケースでも next/prev/get_trading_days の挙動が一貫するように DB 優先・未登録は曜日フォールバックとしている。
- OpenAI クライアント呼び出し部分はテストで差し替え可能（ユニットテスト用に _call_openai_api をモック可）。

今後の TODO（推測）
- ai_scores / market_regime 等のテーブルスキーマ定義をドキュメント化。
- J-Quants クライアント実装（jquants_client の具体的実装とエラー処理の詳細化）。
- 監視・実行（execution）モジュール、モニタリング関連の実装と運用向けドキュメント整備。
- CI テストケース（OpenAI 呼び出しのモック、DuckDB の前提テーブルを用意した統合テスト）。

参考
- この CHANGELOG はソースコード（src/ 以下）からの機能/設計の読み取りに基づく推測的な記述です。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて調整してください。