# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-04
最初の公開リリース。以下の主要機能とモジュールを実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める設定を追加。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装（プロジェクトルート検出は .git / pyproject.toml に依存）。
  - .env パーサーは以下に対応:
    - コメント行・空行無視
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値でのインラインコメント判定
  - .env ロードにおいて OS 環境変数を保護する protected 機能、`.env.local` を `.env` の上書きとして扱う優先度ロジックを実装。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - Settings クラスを提供し、主要設定プロパティを環境変数から安全に取得:
    - J-Quants / kabu API / LINE トークン / DB ファイルパス（DuckDB/SQLite）/監視用パスや閾値/ログレベル/環境種別など。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）と利便性プロパティ（is_live/is_paper/is_dev）を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - 1銘柄あたり記事数・文字数の上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を設けトークン肥大化を抑制。
    - バッチサイズ、リトライ戦略（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）を実装。
    - API レスポンスの堅牢なバリデーション（JSON パース、"results" の存在・型・既知コード照合・数値検証）を実装し、スコアを ±1.0 にクリップ。
    - 部分成功時の DB 書き込みは対象コードに絞って DELETE → INSERT を行い、既存データの保護を行う（DuckDB の制約に配慮）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api をモック可能）。
    - calc_news_window ユーティリティ（対象期間の UTC naive datetime を返す）を実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに書き込む。
    - prices_daily からの MA 計算、raw_news からのマクロキーワード抽出、OpenAI 呼び出し（gpt-4o-mini + JSON mode）、再試行ロジック、結果のクリップ／ラベル付け、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時はマクロセンチメントを 0.0 とするフェイルセーフを採用。
    - モジュール間結合を避けるため、OpenAI 呼び出しは news_nlp の呼び出し実装と独立している。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar テーブル）を扱うユーティリティを実装：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB にカレンダーがない場合は曜日ベース（土日除外）でフォールバックするロジックを実装し、一貫性を保つ設計。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存、バックフィル、健全性チェックを実装。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを集約）。
    - 差分取得・保存・品質チェックの設計方針を実装。DB テーブル存在チェックや最大日付取得等のユーティリティを含む。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離を計算（データ不足時の取り扱いを明示）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - 全て DuckDB を用いた SQL ベース実装、ルックアヘッドバイアス回避。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足時の取り扱い（3 銘柄未満は None）。
    - rank: 同順位は平均ランクを与えるランク関数（丸めて比較することで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリ関数。
  - research パッケージは必要な関数を明示的にエクスポート。

### 修正 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 既知の制限 (Known Issues)
- jquants_client（kabusys.data.jquants_client）や一部外部依存の実装は本リリース内で参照されているが、実装の詳細や外部 API の利用方法は別途提供が必要です（テスト環境でのモック推奨）。
- パッケージの __all__ に strategy / execution / monitoring が含まれていますが、今回のリリースでの実装状況や機能は限定的なため、これらのモジュールは今後拡張される予定です。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を想定。外部 API のレートやレスポンス形式の変化に対してはリトライやパース回復ロジックを用意していますが、実運用前の十分なテストを推奨します。
- DuckDB のバージョン差（executemany の挙動やリスト型バインドの扱い）に注意するため、複数件処理は個別 DELETE / INSERT を用いる実装になっています。

---

参考: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)