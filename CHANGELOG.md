CHANGELOG
=========

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠します。バージョン番号は semver を想定します。

フォーマット
-----------
- "Unreleased" は今後の変更に使用します。
- 各リリースはリリース日（YYYY-MM-DD）を付記します。

Unreleased
----------
- (なし)

[0.1.0] - 2026-03-29
--------------------
Added
- パッケージ初期リリース。モジュール群を公開。
  - 公開 API: kabusys パッケージ（__version__ = 0.1.0）で data / research / ai / 等をエクスポート。

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索してルートを特定（CWD 非依存）。
  - .env パーサ実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - 環境変数保護: OS 環境変数を protected として上書き防止。
  - Settings クラスを実装し、必要な設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして提供。環境値検証（KABUSYS_ENV, LOG_LEVEL）あり。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール: raw_news と news_symbols を用いて銘柄単位にニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JST 基準）: 前日 15:00 ～ 当日 08:30（UTC に変換して DB 比較）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - リトライ/バックオフ: 429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフで再試行。その他エラーはスキップして継続（フォールセーフ）。
    - レスポンス検証: JSON パース、results 配列、コードの照合、数値検証、スコア ±1.0 にクリップ。
    - DuckDB 互換性配慮: executemany に空リスト渡さない等の処理。
    - テスト容易化: _call_openai_api を patch で差し替え可能に設計。
  - regime_detector モジュール: ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し、market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満データのみを使用してルックアヘッドを回避。
    - マクロニュースはキーワードフィルタで抽出、OpenAI 呼び出しのリトライ実装、API エラー時は macro_sentiment=0.0 として継続（フォールセーフ）。
    - 結果はトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等保存。
    - テスト容易化: _call_openai_api を差し替え可能。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理: market_calendar を用いた営業日判定、next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day 等のユーティリティを提供。
    - DB にカレンダーがない場合は土日ベースのフォールバック。DB 登録がある場合は DB 値優先、未登録日は曜日フォールバックで一貫性を確保。
    - 夜間バッチ calendar_update_job を実装し、J-Quants API 経由で差分取得→保存（バックフィル・健全性チェックを実装）。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline と etl の再エクスポート）。
    - ETL パイプライン概念の実装: 差分更新、保存（jquants_client への委譲）、品質チェック（quality モジュール統合）を想定した設計。
    - 最終取得日取得、テーブル存在チェック等のユーティリティを実装。

- Research モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M のリターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）およびバリュー（PER、ROE）を DuckDB の prices_daily / raw_financials テーブルから計算する関数を提供。
    - データ不足時の None 処理、詳細な SQL 実装、ログ出力を実装。
  - feature_exploration:
    - 将来リターン算出（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - rank 関数は丸めによる ties の扱いを配慮。
  - research パッケージは主要関数を top-level に再エクスポート。

Changed
- 初期リリースのため「Changed」は該当なし。

Fixed
- 初期リリースのため「Fixed」は該当なし。
  - 実装上の堅牢性: DuckDB の executemany 空リスト制約や API レスポンス不正時のフォールバック等、実運用での問題を想定した防御的実装を多数追加。

Security
- OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を送出して誤操作を防止。

Notes / Implementation details
- OpenAI モデル: gpt-4o-mini を想定し、JSON Mode を利用（response_format={"type":"json_object"}）。
- バッチ/トリム設定: ニュース処理は銘柄ごと最大 10 記事、3000 文字、API バッチは最大 20 銘柄。
- ルックアヘッド防止: 各処理は date / target_date ベースで設計し、datetime.today()/date.today() を直接参照しない方針。
- トランザクション安全: 主要テーブル更新は BEGIN/DELETE/INSERT/COMMIT を使い、例外時は ROLLBACK を試行。
- テスト支援: OpenAI 呼出し部分はモック差し替えが容易に。DuckDB ベースの処理は SQL を明示してテスト可能。

Authors
-------
- 初回実装: 開発チーム（コードベースの内容から推測して記載）

ライセンス
---------
- リポジトリに従う（ここでは明記なし。実際のリポジトリの LICENSE を参照してください）。