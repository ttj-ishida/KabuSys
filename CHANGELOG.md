CHANGELOG
=========
すべての変更は Keep a Changelog の方針に準拠しています。  
日付はリリース時点での暫定値です（コードから推測して作成）。

Unreleased
----------
（なし）

0.1.0 - 2026-04-01
-----------------
最初の公開リリース相当。以下の主要な機能実装と堅牢化を含みます。

追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。公開モジュールを __all__ に定義。
- 環境設定 / .env 管理
  - .env ファイルおよび環境変数から設定を読み込む設定モジュールを追加（src/kabusys/config.py）。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を探索）し、配布後も動作するよう設計。
  - .env の自動読み込み順序を定義：OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを実装（クォート文字・バックスラッシュエスケープ対応、export プレフィックス対応、インラインコメント処理）。無効行はスキップ。
  - OS 環境変数を保護する protected セット機能を導入し、明示的な override 動作を実装。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB /監視 /システム設定等のプロパティを提供（必須変数は _require() により未設定時に ValueError を送出）。
- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン結果表現用のデータクラス ETLResult を実装し公開（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py で再エクスポート）。
  - JPX マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）：
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - データ未取得時は曜日ベース（週末は休業）でフォールバックする一貫したロジックを実装。
    - calendar_update_job により J-Quants から差分取得して冪等保存するジョブを追加（バックフィル、健全性チェック含む）。
  - DuckDB 操作の互換性や実運用上の制約（例：executemany に空リスト不可）を考慮した実装。
- 研究・リサーチ関連
  - research パッケージを追加（src/kabusys/research/**）:
    - factor_research モジュール：calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials のみ参照）。
    - feature_exploration モジュール：calc_forward_returns, calc_ic, factor_summary, rank を実装（外部依存なし）。
    - data.stats の zscore_normalize を再エクスポートする __init__ を用意。
- AI（OpenAI を用いた NLP）
  - ニュースセンチメント分析モジュールを追加（src/kabusys/ai/news_nlp.py）：
    - raw_news と news_symbols を集約し、銘柄ごとに gpt-4o-mini（JSON mode）でスコアリングして ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/チャンク）、トリム（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）を行い、部分失敗時に既存スコアを保護する置換ロジック（DELETE→INSERT）を実装。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）：
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次でレジーム（bull/neutral/bear）を判定、market_regime テーブルに冪等書き込み。
    - マクロニュース取得（マクロキーワード）→ OpenAI（gpt-4o-mini）呼び出し→スコア合成のフローを実装。API 失敗時はフェイルセーフで macro_sentiment=0.0 を使用。
    - API コールのリトライ/バックオフ処理と JSON パースの堅牢化を実装。
- その他ユーティリティ
  - news_nlp の calc_news_window を公開して他モジュール（regime_detector 等）が利用可能に。
  - 各モジュールで「ルックアヘッドバイアス防止」の設計方針を徹底（datetime.today()/date.today() を参照せず、target_date 引数を必須にする）。

変更 (Changed)
- DuckDB 操作に関する互換性配慮を明文化（executemany の空リスト回避等）。
- API エラー処理を一貫化（openai の APIError の status_code に対する保守的な扱い、5xx のみ再試行等）。
- レスポンスパース失敗や API 未設定時の挙動を明確化（ValueError を投げる場所、フェイルセーフで 0.0 を返す場所の区別）。

修正 (Fixed)
- .env パーサの以下の課題に対応:
  - export プレフィックスをサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実装。
  - クォートなしの値におけるインラインコメント（#）の取り扱いを改善（前が空白/タブでない場合はコメント扱いしない）。
- OpenAI 呼び出し系の堅牢化:
  - JSON モードでも前後に余計なテキストが混じるケースを考慮して最外の {} を抽出して復元するロジックを追加（ニュース NLP）。
  - レート制限/タイムアウト/ネットワーク断/5xx に対して指数バックオフを実装し、最終的に安全なフォールバックを行う。
- DB 書き込みの堅牢化:
  - market_regime / ai_scores への書き込みを冪等化（BEGIN / DELETE / INSERT / COMMIT + ROLLBACK の取り扱い）して部分失敗時の副作用を抑制。
  - DuckDB の日付型・NULL に対する安全な扱いを実装（_to_date 等）。

セキュリティ（Security）
- .env 読み込み時に OS の環境変数を protected セットとして扱い、誤って OS 環境を上書きしない挙動を採用。
- API キーが未設定の場合は早期に ValueError を投げ、実行時に秘匿トークンが不要に露出しないように注意喚起。

ドキュメント（Documentation）
- 各モジュールに処理フロー・設計方針・注意点を詳述したドキュメンテーション文字列（docstring）を追加。特にルックアヘッドバイアス防止、テストしやすさ、DuckDB 互換性等について明示。

既知の制限 / 注意点 (Known issues / Notes)
- OpenAI 依存部分は実行時に API キー（OPENAI_API_KEY）を必要とする。CI/テストでは _call_openai_api をパッチして外部呼び出しをモックすることを想定。
- DuckDB バインドの挙動（特に executemany に空リストを渡せない点）に依存するため、ETL の空結果処理は注意が必要。
- 一部モジュール（例: 発注/実行関連の execution, monitoring）は __all__ に含まれているが、このリリースでの実装内容は限定的または別ファイルで管理される想定。

補足
- ソースコード中の多くの設計判断（例: フェイルセーフ、冪等性、テスト容易性、外部依存分離）は docstring に明記されています。運用・テスト計画を立てる際は該当 docstring を参照してください。

---
この CHANGELOG はコードベースの内容（docstring、関数名、実装パターン）から推測して作成しています。不明点や日付の調整、さらに細かな差分区分が必要な場合はソース管理ログ（git commit）に基づく実際の履歴と照合してください。