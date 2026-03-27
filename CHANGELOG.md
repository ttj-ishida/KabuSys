Keep a Changelog 準拠の CHANGELOG.md（日本語、コードベースから推測）

注意: 以下は提供されたソースコードの内容から実装済み機能・設計判断・フェイルセーフ挙動などを推測してまとめた変更履歴（初期リリース想定）です。

フォーマットは Keep a Changelog に準拠しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-27
-------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にてバージョン __version__ = "0.1.0" を設定。
    - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定。配布後の動作にも配慮。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - OS 環境変数は protected セットとして上書きを防止。
  - .env パーサの強化:
    - export KEY=val 形式やシングル/ダブルクォート内でのバックスラッシュエスケープに対応。
    - クォートなしの場合のインラインコメント処理（直前が空白/タブの場合に '#' をコメントと認識）。
  - 必須設定取得用 _require と Settings のプロパティを提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル検証等）。
  - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）。

- AI モジュール（src/kabusys/ai）
  - ニュースNLP: score_news（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書込む。
    - バッチサイズ、記事/文字列のトリム、JSON Mode の利用、レスポンスバリデーションを実装。
    - 失敗時の挙動: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、非リトライエラーはスキップして処理継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。部分失敗時でも既存スコアを保護するためコードを限定して DELETE→INSERT（冪等）を実施。
    - テスト容易性: _call_openai_api をモジュール内で分離して unittest.mock.patch により差し替え可能。
    - 時間ウィンドウ設計（JST基準 → DB 比較は UTC naive datetime）とルックアヘッドバイアス回避（date.today() を直接参照しない）。
  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を計算。
    - OpenAI 呼び出しは JSON Mode を利用。API 呼び出し用関数は news_nlp と別実装にしてモジュール結合を避ける。
    - LLM 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。スコアはクリップし閾値でラベリング。
    - DuckDB への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保、失敗時は ROLLBACK を試行。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日列挙・SQ 日判定のユーティリティを提供。
    - DB データが一部欠けている場合は DB 値を優先し未登録日は曜日（土日）フォールバックで扱う一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 探索の最大範囲制限や健全性チェックにより無限ループや異常データを回避。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスで ETL 結果（取得数・保存数・品質問題・エラー）を集約、to_dict により品質問題をシリアライズ可能。
    - 差分更新（最終取得日から未取得範囲を自動算出）、backfill による後出し修正吸収、品質チェック（quality モジュール連携）などの設計方針を実装。
    - jquants_client（外部モジュール）を経由した取得/保存処理に対応。
    - DB テーブル存在チェックや最大日付取得のユーティリティを提供。
    - src/kabusys/data/etl.py で ETLResult を外部公開。

- リサーチ機能（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金, 出来高比）を DuckDB の prices_daily / raw_financials を元に計算する関数を提供。
    - データ不足時の None ハンドリング、営業日スキャンバッファなど実用上の配慮を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman 相関）計算、ランク変換 util（rank）、factor_summary（基本統計量）などを実装。
    - 外部フレームワークに依存せず標準ライブラリと DuckDB で完結する設計。
  - モジュール公開（src/kabusys/research/__init__.py）:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank を公開。

- 共通設計・運用上の配慮（全体）
  - DuckDB を主要な分析 DB として利用。トランザクションや executemany の挙動（空パラメータ回避）に配慮した実装。
  - ルックアヘッドバイアスを招かないため、日時の解決は関数引数（target_date 等）に依存し、date.today()/datetime.today() を直接参照しない設計。
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスパースの堅牢化（前後余計なテキストが混入する場合の復元）を実装。
  - テスト容易性を考慮し、API キー注入や _call_openai_api の差し替えを可能にしている。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- 機微情報の保護:
  - 環境変数の読み込みにおいて、既存の OS 環境変数は保護され上書きされない設計（protected set）。
  - OpenAI API キーは引数注入または OPENAI_API_KEY 環境変数で提供。キー未設定時は ValueError を投げ早期に検出。

既知の制約・注意点（コードから推測）
- OpenAI 依存部分はネットワークや API の制約に影響されるため、API 側の仕様変更やモデル名（gpt-4o-mini 等）の変更に注意が必要。
- 日時はモジュール内で UTC naive な datetime を扱う箇所があり、外部と日時をやり取りする際はタイムゾーン扱いに注意が必要。
- 一部の集約処理は DuckDB のバージョン差異（リスト型バインドなど）に配慮した実装になっているが、DB バージョン依存の動作確認は必要。

貢献・テストに関するヒント
- OpenAI 呼び出しはモジュール単位で _call_openai_api を差し替えてモック可能（unittest.mock.patch を想定）。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できるため、テスト環境ではこれを設定しておくと安全。

（以上）