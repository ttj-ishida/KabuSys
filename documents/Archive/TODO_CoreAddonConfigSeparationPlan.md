# Core Config Separation Plan

> **ステータス: 完了（2026-05-10）** — Issue #284 対応済み。Archive 移動済み。

`Issue 4` として、`Core` と `Addon` の設定項目分離方針を整理した記録。

この文書の目的は、現行の `.env` / `Settings` / `validate_config` / `config_setup` に同居している設定を、

- `Core` に残すもの
- `Addon` 側へ移すもの
- 一時的に `Core` に残すが、将来移設するもの

に分けること。

## 1. 結論

現状の `KabuSys` は、`Core` と `Addon` の設定が `.env` と `Settings` に同居している。  
別 repo 化を前提にすると、次の方針が自然。

- `Core` 必須設定はそのまま `Core` に残す
- `Addon` 固有の有効化フラグと認証情報は、最終的に `Addon` 側設定へ移す
- 移行期間中は `Core` 側に no-op トグルを残してもよいが、`Core` セットアップ手順からは外す

## 2. 現行の設定導線

現状で設定の主な入口は次。

- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:1)
- [src/kabusys/config_setup.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config_setup.py:1)
- [src/kabusys/validate_config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/validate_config.py:1)
- [documents/WebManual/B_CoreSetup.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/B_CoreSetup.md:87)

ここに `Core` 用と `Addon` 用が混在している。

## 3. Core に残す設定

次は `Core` 単体での実行に必須、または妥当な設定。

### 3.1 実行環境・基盤

- `KABUSYS_ENV`
- `DUCKDB_PATH`
- `SQLITE_PATH`
- `LOG_LEVEL`
- `PAPER_TRADING_INITIAL_CASH`

理由:

- `Core` の起動モード、DB、ログ、paper 実行に直結するため

### 3.2 売買基盤

- `JQUANTS_REFRESH_TOKEN`
- `JQUANTS_BULK_API_KEY`
- `KABU_API_PASSWORD`
- `KABU_API_BASE_URL`
- `KABU_TRADE_PASSWORD`
- `KABU_USE_SANDBOX`
- `KABU_SANDBOX_API_PASSWORD`

理由:

- データ取得と売買実行の最低限基盤だから

## 4. Addon 側へ移す設定

次は `Core` 単体では不要で、別 repo 側に寄せるべき設定。

### 4.1 AI Addon

- `ENABLE_AI_SENTIMENT`
- `OPENAI_API_KEY`

現行参照:

- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:177)
- [src/kabusys/ai/news_nlp.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/ai/news_nlp.py:134)
- [src/kabusys/ai/regime_detector.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/ai/regime_detector.py:312)

理由:

- OpenAI 依存であり、`Core` 単体のセットアップ条件にすべきではないため

### 4.2 Disclosure Addon

- `ENABLE_TDNET`
- `ENABLE_EDINET`
- `EDINET_API_KEY`

現行参照:

- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:186)
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:196)
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:206)
- [scripts/run_tdnet_collection.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_tdnet_collection.py:1)
- [scripts/run_edinet_collection.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_edinet_collection.py:1)

理由:

- 外部開示ソースの拡張機能であり、`Core` の必須導線ではないため

### 4.3 News Source Addon

- `ENABLE_YAHOONEWS`

現行参照:

- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:214)
- [scripts/run_yahoonews_collection.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_yahoonews_collection.py:1)

理由:

- Yahoo News 収集自体を `Addon` と決めているため

### 4.4 Notification Addon

- `LINE_NOTIFY_ENABLED`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`

現行参照:

- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:225)
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:229)
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:232)
- [src/kabusys/operations/notifier.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/operations/notifier.py:91)

理由:

- 外部通知基盤であり、`Core` 実行に必須ではないため

## 5. 暫定的に Core に残してよい設定

移行期間中は、次の考え方で `Core` 側に残してもよい。

- `ENABLE_AI_SENTIMENT`
- `ENABLE_TDNET`
- `ENABLE_EDINET`
- `ENABLE_YAHOONEWS`
- `LINE_NOTIFY_ENABLED`

ただし役割は「機能有効化」ではなく、`Addon` 未導入時の no-op 互換用とする。

つまり、

- `Core` セットアップでは積極的に案内しない
- 値がなくても `validate_config` で失敗させない
- `Addon` 側導入時だけ意味を持つ

という扱いに寄せる。

## 6. validate_config の整理方針

現状では optional 項目が `Core` 側 validator に入っている。

- [src/kabusys/validate_config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/validate_config.py:43)
- [src/kabusys/validate_config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/validate_config.py:314)

分離方針は次。

### 6.1 Core validator に残すもの

- `Core` 必須設定
- `Core` で推奨されるパスや基本実行条件

### 6.2 Core validator から外すもの

- `OPENAI_API_KEY`
- `EDINET_API_KEY`
- LINE 認証情報の本番警告

理由:

- これらは `Addon` 未導入なら無関係だから

### 6.3 移行期の扱い

- `Core` validator では `info` か `warning` に落とす
- 将来的には `addon validate` 側へ移す

## 7. config_setup の整理方針

現状では `config_setup.py` が `Core` と `Addon` の両方を対話対象にしている。

- [src/kabusys/config_setup.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config_setup.py:21)
- [src/kabusys/config_setup.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config_setup.py:111)

分離方針は次。

### 7.1 Core setup に残すもの

- `KABUSYS_ENV`
- `JQUANTS_*`
- `KABU_*`
- `DUCKDB_PATH`
- `SQLITE_PATH`
- `PAPER_TRADING_INITIAL_CASH`
- `LOG_LEVEL`

### 7.2 Core setup から外すもの

- LINE 設定
- AI 設定
- TDnet / EDINET 設定
- Yahoo News 設定

### 7.3 将来の形

- `core config setup`
- `addon ai config setup`
- `addon disclosure config setup`
- `addon news config setup`
- `addon notification config setup`

のように責務を分けるのが自然。

## 8. WebManual の整理方針

現状の [B_CoreSetup.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/B_CoreSetup.md:87) には、`Core` 設定と `Addon` 設定が同じ表に並んでいる。

別 repo 化を前提にすると、次のように分けるのが自然。

### 8.1 Core Manual に残すもの

- `Core` 必須設定一覧
- `paper/live` 基本導線
- DB / scheduler / validation

### 8.2 Addon Manual に出すもの

- AI センチメント設定
- TDnet / EDINET 設定
- Yahoo News 設定
- LINE 通知設定

### 8.3 移行期の書き方

- `Core` Manual では「Addon で有効化可能」とだけ触れる
- 詳細手順は Addon 側文書へ逃がす

## 9. 優先順位

設定分離の TODO は次の順で進めるのがよい。

1. `Core` 必須設定一覧を確定する
2. `Addon` 固有設定を責務別に分類する
3. `validate_config` の `Core` 対象範囲を定義する
4. `config_setup` の `Core` 対象範囲を定義する
5. `WebManual` の `Core setup` 記述範囲を見直す

## 10. この Issue での成果

この `Issue 4` では、まだ実装修正はしない。  
成果物は次の 3 点。

- `Core` に残す設定の範囲
- `Addon` 側へ移す設定の範囲
- `validate_config` / `config_setup` / `WebManual` をどこまで `Core` 扱いにするかの判断材料

## 11. 関連

- [TODO_CoreAddonRepoSplit.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonRepoSplit.md)
- [TODO_CoreAddonResponsibilityMatrix.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonResponsibilityMatrix.md)
- [TODO_CoreAddonExtensionPoints.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonExtensionPoints.md)
- [TODO_CoreAddonImportBoundaryAudit.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonImportBoundaryAudit.md)
