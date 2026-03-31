Keep a Changelog
すべての重要な変更履歴をこのファイルで管理します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- （現在未リリースの変更はありません）

0.1.0 - 2026-03-31
Added
- 基本パッケージ初期実装
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0", __all__ の公開）。
- 環境変数 / 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（読み込み優先順位: OS > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点）。
  - .env ファイルパーサを実装（export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いに対応）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等を取得・検証。
  - 必須環境変数未設定時は分かりやすい例外を送出する _require 実装。
- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング (kabusys.ai.news_nlp)
    - 指定タイムウィンドウ（JST: 前日15:00〜当日08:30、内部は UTC naive で扱う）に基づくニュース抽出。
    - news_symbols と raw_news を銘柄ごとに集約し、1銘柄あたりの最新記事数と文字数を制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI (gpt-4o-mini, JSON mode) へバッチ送信（チャンクサイズ: 最大 20 銘柄）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行ロジックを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、コード正規化、スコア数値チェック、±1.0 でクリップ）。
    - DuckDB への書き込みは部分置換（対象コードだけ DELETE → INSERT）で部分失敗から既存データを保護。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出用キーワード群、最大記事数、LLM モデル名（gpt-4o-mini）、リトライポリシー等を定義。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ設計。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - ルックアヘッドバイアス対策: date 引数ベースで処理し、today() を参照しない。
- データプラットフォーム（kabusys.data）
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末除外）で一貫性を確保。
    - カレンダー夜間バッチ更新 job を実装（J-Quants API から差分取得し冪等で保存、バックフィル・健全性チェックあり）。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー情報を含む）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）との連携方針を実装。
    - jquants_client を使った取得・保存処理（fetch/save）を想定した設計。
  - etl 入口モジュールで ETLResult を再エクスポート。
- リサーチモジュール (kabusys.research)
  - factor_research: momentum / volatility / value 計算実装
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None、営業日ベースの窓）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB SQL とウィンドウ関数を活用した効率的実装。
  - feature_exploration: 将来リターン / IC / 統計
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証と最大ホライズンに基づくスキャン範囲制約を実装。
    - calc_ic: スピアマン（ランク相関）で IC を算出。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランク、丸めで ties の検出漏れを軽減。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリで計算。
- パッケージ初期エクスポート設定
  - 各サブパッケージ（ai, data, research 等）の __init__ で主要関数を再エクスポートし、公開 API を整理。

Security
- 特になし。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- なし。

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策: ほとんどの処理は target_date 引数ベースで動作し、datetime.today()/date.today() を直接参照しない設計になっています（再現性とテスト性を重視）。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode を活用、レスポンスパースや例外処理に冗長なフェイルセーフを実装。
- DuckDB に依存した実装。executemany の空リスト渡し回避など、DuckDB のバージョン挙動への互換性配慮があります。
- 外部 API キーは引数で注入可能（テスト容易性）、未設定時は環境変数 OPENAI_API_KEY を参照して ValueError を送出。

今後の予定（例）
- 発注・実行（execution）や監視（monitoring）の具体実装の追加
- 単体テスト・統合テストの充実、CI ワークフローの整備
- ドキュメント（設計ドキュメント・使用例）の拡充

もし特定のリリースノートの表現をより簡潔・詳細にしたい場合や、日付やバージョン表記の変更を希望される場合は指示ください。